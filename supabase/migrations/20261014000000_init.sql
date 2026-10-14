-- Lincoln's Inn Fields court notifier: members, watches, the slot snapshot and the scan.
--
-- Plain Postgres 16, no Supabase-only features, so CI can run it on a stock container.
-- All dates and hours are London-local. london_now() is the only clock: nothing
-- else in a migration may read the time (CI checks this).

-- Supabase has service_role; a plain Postgres doesn't, so create it as Supabase does.
do $$
begin
  if not exists (select from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end
$$;

-- --- the clock ------------------------------------------------------------

-- London-local wall-clock time. Tests pin it with set_config('app.now', ..., true).
create function london_now() returns timestamp
language sql stable
set search_path = pg_catalog
as $$
  select coalesce(
    nullif(current_setting('app.now', true), '')::timestamp,
    now() at time zone 'Europe/London'
  )
$$;

-- The last bookable day: slots after it are stored but "not open".
create function window_end() returns date
language sql stable
set search_path = public, pg_catalog
as $$
  select london_now()::date + 34
$$;

-- --- tables ---------------------------------------------------------------

create table member (
  id bigint generated always as identity primary key,
  telegram_id bigint not null unique,
  first_name text not null,
  username text,
  is_owner boolean not null default false,
  joined_at timestamp not null default london_now(),
  unreachable_since timestamp
);

-- One chosen hour: weekly (ISO weekday, Mon = 1) or single-date, never both.
create table watch (
  id bigint generated always as identity primary key,
  member_id bigint not null references member on delete cascade,
  weekday smallint check (weekday between 1 and 7),
  date date,
  hour smallint not null check (hour between 0 and 23),
  check ((weekday is null) <> (date is null)),
  unique nulls not distinct (member_id, weekday, date, hour)
);

-- The snapshot. A future slot missing from a complete scan is kept, never deleted.
create table slot (
  court smallint not null check (court between 1 and 3),
  date date not null,
  hour smallint not null check (hour between 0 and 23),
  status text not null check (status in ('free', 'booked')),
  status_since timestamp not null,
  last_seen_at timestamp not null,
  primary key (court, date, hour)
);

create table slot_change (
  id bigint generated always as identity primary key,
  court smallint not null,
  date date not null,
  hour smallint not null,
  from_status text not null,
  to_status text not null,
  at timestamp not null
);

create table alert (
  id bigint generated always as identity primary key,
  member_id bigint not null references member on delete cascade,
  court smallint not null,
  date date not null,
  hour smallint not null,
  kind text not null check (kind in ('cancellation', 'release', 'new_watch')),
  created_at timestamp not null default london_now(),
  sent_at timestamp,
  failures integer not null default 0,
  last_error text
);

-- One row per court per scan attempt.
create table scan_log (
  id bigint generated always as identity primary key,
  at timestamp not null,
  court smallint not null,
  ok boolean not null,
  slots integer,
  error text
);

-- The browser never reads tables; everything goes through the Edge Function.
alter table member enable row level security;
alter table watch enable row level security;
alter table slot enable row level security;
alter table slot_change enable row level security;
alter table alert enable row level security;
alter table scan_log enable row level security;

grant select, insert, update, delete on member, watch, slot, slot_change, alert, scan_log to service_role;

-- --- record_scan ----------------------------------------------------------

-- Applies one scan of the courts. `courts` is a list of scan_court results:
-- {"court": 1, "weeks": 6, "slots": [{"date", "hour", "status"}], "error"?}.
-- A court is applied only if it is complete: all 6 weeks parsed and at least
-- half the slots it had last time. Otherwise its stored slots are left as they
-- were, so a half-scan can't fake mass changes. Every court gets a scan_log row.
-- Each court is applied on its own: if one court's data can't be stored (a
-- duplicate slot, a bad court number), only that court is rolled back, logged and
-- listed in "failed", so the caller can fail its job while the others still apply.
create function record_scan(courts jsonb) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  c jsonb;
  n smallint;
  scanned integer;
  previous integer;
  problem text;
  complete smallint[] := '{}';
  failed jsonb := '[]';
begin
  for c in select * from jsonb_array_elements(courts) loop
    n := null;
    scanned := null;
    begin
      n := (c->>'court')::smallint;
      scanned := jsonb_array_length(coalesce(c->'slots', '[]'));
      select count(*) into previous from slot
      where court = n and last_seen_at = (select max(last_seen_at) from slot where court = n);

      problem := case
        when coalesce((c->>'weeks')::integer, 0) < 6 then
          coalesce(c->>'error', format('%s of 6 weeks', coalesce((c->>'weeks')::integer, 0)))
        when scanned * 2 < previous then
          format('%s slots, below half of the previous %s', scanned, previous)
      end;
      if problem is not null then
        insert into scan_log (at, court, ok, slots, error) values (london_now(), n, false, scanned, problem);
        continue;
      end if;

      -- Both parts read the snapshot as it was before this statement. Slots missing
      -- from the scan are left alone, so booked -> missing -> free still logs booked -> free.
      with scanned as (
        select (s->>'date')::date as date, (s->>'hour')::smallint as hour, s->>'status' as status
        from jsonb_array_elements(c->'slots') s
      ), changes as (
        insert into slot_change (court, date, hour, from_status, to_status, at)
        select n, sc.date, sc.hour, sl.status, sc.status, london_now()
        from scanned sc
        join slot sl on (sl.court, sl.date, sl.hour) = (n, sc.date, sc.hour)
        where sl.status <> sc.status
      )
      insert into slot as sl (court, date, hour, status, status_since, last_seen_at)
      select n, date, hour, status, london_now(), london_now() from scanned
      on conflict (court, date, hour) do update set
        status = excluded.status,
        status_since = case when sl.status = excluded.status then sl.status_since else excluded.status_since end,
        last_seen_at = excluded.last_seen_at;
      insert into scan_log (at, court, ok, slots, error) values (london_now(), n, true, scanned, null);
      complete := complete || n;
    exception when others then
      -- The block's own work is rolled back; log the court as failed instead.
      insert into scan_log (at, court, ok, slots, error)
      values (london_now(), n, false, scanned, 'not recorded: ' || sqlerrm);
      failed := failed || jsonb_build_object('court', n, 'error', sqlerrm);
    end;
  end loop;
  return jsonb_build_object('all_complete', complete @> '{1,2,3}', 'failed', failed);
end
$$;

-- The project doesn't expose new objects automatically: only service_role
-- (the poller and the Edge Function) may call the functions.
revoke execute on all functions in schema public from public;
do $$
begin
  if exists (select from pg_roles where rolname = 'anon') then
    revoke execute on all functions in schema public from anon, authenticated;
    alter default privileges in schema public revoke execute on functions from anon, authenticated;
  end if;
end
$$;
grant execute on all functions in schema public to service_role;

-- The grants above cover only what exists now. These make later migrations'
-- tables and functions (created by the same migration role) follow suit.
-- PUBLIC's execute is a global default, which a per-schema rule can't revoke.
alter default privileges revoke execute on functions from public;
alter default privileges in schema public grant execute on functions to service_role;
alter default privileges in schema public grant select, insert, update, delete on tables to service_role;
