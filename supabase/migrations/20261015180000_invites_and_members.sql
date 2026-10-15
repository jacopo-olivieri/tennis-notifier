-- Invites and members: the owner makes single-use invite links and manages who is
-- in; a friend redeems a link at login. Owner-only functions refuse anyone else
-- with SQLSTATE 42501, which the Edge Function turns into a 403.

-- Only the token's hash is stored; the raw token goes out once, in the link.
create table invite (
  id bigint generated always as identity primary key,
  token_hash text not null unique,
  created_at timestamp not null default london_now(),
  expires_at timestamp not null default london_now() + interval '7 days',
  used_by bigint references member on delete set null,
  used_at timestamp,
  revoked_at timestamp
);
alter table invite enable row level security;

create function hash_token(token text) returns text
language sql immutable
set search_path = pg_catalog
as $$
  select encode(sha256(convert_to(token, 'UTF8')), 'hex')
$$;

-- Raises unless `member_id` is the owner.
create function require_owner(member_id bigint) returns void
language plpgsql stable
set search_path = public, pg_catalog
as $$
begin
  if not exists (select from member m where m.id = require_owner.member_id and m.is_owner) then
    raise exception 'owner only' using errcode = 'insufficient_privilege';
  end if;
end
$$;

-- --- login ----------------------------------------------------------------

-- As before for an existing member, who leaves any invite token unused. Anyone
-- else with an invite token that is unused, unexpired and unrevoked becomes a
-- member and uses it up; with any other token they get {"status": "invite_invalid"}.
create or replace function login(telegram_user jsonb, invite_token text) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  signed_in bigint;
  redeemed bigint;
begin
  update member set
    first_name = telegram_user->>'first_name',
    username = telegram_user->>'username'
  where telegram_id = (telegram_user->>'id')::bigint
  returning id into signed_in;
  if signed_in is not null then
    return jsonb_build_object('status', 'member', 'member_id', signed_in);
  end if;
  if invite_token is null then
    return jsonb_build_object('status', 'not_member');
  end if;

  -- One statement claims the invite, so two people racing for it can't both win.
  update invite set used_at = london_now()
  where token_hash = hash_token(invite_token)
    and used_at is null and revoked_at is null and expires_at > london_now()
  returning id into redeemed;
  if redeemed is null then
    return jsonb_build_object('status', 'invite_invalid');
  end if;

  insert into member (telegram_id, first_name, username)
  values ((telegram_user->>'id')::bigint, telegram_user->>'first_name', telegram_user->>'username')
  returning id into signed_in;
  update invite set used_by = signed_in where id = redeemed;
  return jsonb_build_object('status', 'member', 'member_id', signed_in);
end
$$;

-- --- the owner's functions ------------------------------------------------

-- A new invite, as {"id", "token", "expires_at"}. The token is never stored.
create function create_invite(owner_id bigint) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
  created invite;
begin
  perform require_owner(owner_id);
  insert into invite (token_hash) values (hash_token(token)) returning * into created;
  return jsonb_build_object('id', created.id, 'token', token, 'expires_at', created.expires_at);
end
$$;

-- Revokes an invite not yet used; a used or already revoked one is left alone.
create function revoke_invite(owner_id bigint, invite_id bigint) returns void
language plpgsql
set search_path = public, pg_catalog
as $$
begin
  perform require_owner(owner_id);
  update invite set revoked_at = london_now()
  where id = invite_id and used_at is null and revoked_at is null;
end
$$;

-- The invites that could still be redeemed, oldest first.
create function list_invites(owner_id bigint) returns jsonb
language plpgsql stable
set search_path = public, pg_catalog
as $$
begin
  perform require_owner(owner_id);
  return coalesce((
    select jsonb_agg(jsonb_build_object('id', id, 'created_at', created_at, 'expires_at', expires_at) order by id)
    from invite
    where used_at is null and revoked_at is null and expires_at > london_now()
  ), '[]');
end
$$;

-- Every member, the owner first, with how many hours they watch: weekly ones
-- and single-date ones that haven't started.
create function list_members(owner_id bigint) returns jsonb
language plpgsql stable
set search_path = public, pg_catalog
as $$
begin
  perform require_owner(owner_id);
  return (
    select jsonb_agg(jsonb_build_object(
      'id', m.id, 'first_name', m.first_name, 'username', m.username, 'is_owner', m.is_owner,
      'hours', (select count(*) from watch w where w.member_id = m.id
        and (w.date is null or w.date + make_interval(hours => w.hour) > london_now()))
    ) order by m.is_owner desc, m.joined_at, m.id)
    from member m
  );
end
$$;

-- A hard delete: their watches and alerts go with them. The owner can't be removed.
create function remove_member(owner_id bigint, member_id bigint) returns void
language plpgsql
set search_path = public, pg_catalog
as $$
begin
  perform require_owner(owner_id);
  if exists (select from member m where m.id = remove_member.member_id and m.is_owner) then
    raise exception 'the owner cannot be removed' using errcode = 'insufficient_privilege';
  end if;
  delete from member m where m.id = remove_member.member_id;
end
$$;
