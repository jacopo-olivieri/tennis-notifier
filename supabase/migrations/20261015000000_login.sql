-- Signing in: the Edge Function checks the Telegram Login Widget's signature,
-- then login() decides who that is, and member_state() is what the site shows.

-- `telegram_user` is the verified widget payload ({"id", "first_name", "username"?, ...}).
-- An existing member gets their name and username refreshed and comes back as
-- {"status": "member", "member_id"}; anyone else is {"status": "not_member"}.
-- `invite_token` is for redeeming an invite link, which isn't built yet.
create function login(telegram_user jsonb, invite_token text) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  signed_in bigint;
begin
  update member set
    first_name = telegram_user->>'first_name',
    username = telegram_user->>'username'
  where telegram_id = (telegram_user->>'id')::bigint
  returning id into signed_in;
  if signed_in is null then
    return jsonb_build_object('status', 'not_member');
  end if;
  return jsonb_build_object('status', 'member', 'member_id', signed_in);
end
$$;

-- What GET /state returns for a signed-in member, or null once they've been removed.
create function member_state(member_id bigint) returns jsonb
language sql stable
set search_path = public, pg_catalog
as $$
  select jsonb_build_object('member', jsonb_build_object(
    'first_name', m.first_name, 'username', m.username, 'is_owner', m.is_owner
  ))
  from member m
  where m.id = member_state.member_id
$$;
