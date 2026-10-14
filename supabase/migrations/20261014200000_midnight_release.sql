-- The midnight release: one release run claims the night, regular scans stand
-- aside while it holds the claim, and record_release alerts every watched slot
-- free on the newly opened day.

-- --- tables ---------------------------------------------------------------

-- Once-a-day jobs: kind 'release' (for_date is the day that opens at midnight)
-- and 'heads_up'. A run claims one by inserting its row.
create table marker (
  kind text not null check (kind in ('release', 'heads_up')),
  for_date date not null,
  claimed_by text not null,
  claimed_at timestamp not null,
  done_at timestamp,
  primary key (kind, for_date)
);

alter table marker enable row level security;

-- --- the release claim ----------------------------------------------------

-- Whether `day` is tonight's release, from 23:30 before the midnight it opens
-- until 00:15 after: the day that opens at the coming midnight
-- (window_end() + 1), or the day that just opened (window_end()).
create function release_due(day date) returns boolean
language sql stable
set search_path = public, pg_catalog
as $$
  select day = window_end() + 1 and london_now()::time >= '23:30'
      or day = window_end() and london_now()::time < '00:15'
$$;

-- Claims the release of `day` for run_id. True if this run holds the claim,
-- whether it just took it or already had it (a re-run keeps its run id). A
-- claim is only taken while the release is due, so a run dispatched at any
-- other time can't stop the scans.
create function claim_release(day date, run_id text) returns boolean
language sql
set search_path = public, pg_catalog
as $$
  insert into marker (kind, for_date, claimed_by, claimed_at)
  select 'release', day, run_id, london_now()
  where release_due(day)
  on conflict do nothing;
  select coalesce((select claimed_by = run_id from marker where (kind, for_date) = ('release', day)), false);
$$;

-- True while tonight's release is claimed and not done, until 00:15 London.
-- Regular scans exit at once while it holds, so exactly one poller runs.
create function release_claim_held() returns boolean
language sql stable
set search_path = public, pg_catalog
as $$
  select exists (
    select from marker where kind = 'release' and done_at is null and release_due(for_date)
  )
$$;

-- --- formatting -----------------------------------------------------------

-- As before, plus the release headline.
create or replace function alert_messages(ids bigint[]) returns jsonb
language sql stable
set search_path = public, pg_catalog
as $$
  with alerts as (
    select * from alert where id = any(ids)
  ), lines as (
    select member_id, date, hour, format('%s %s:00  %s',
      to_char(date, 'Dy FMDD Mon'),
      lpad(hour::text, 2, '0'),
      string_agg(format('<a href="%s">C%s</a>', court_page(court), court), ' ' order by court)
    ) as line
    from alerts group by member_id, date, hour
  ), messages as (
    select member_id,
      case
        when count(distinct kind) > 1 then '🎾 Free now'
        when bool_and(kind = 'release') then '🎾 Just released'
        when bool_and(kind = 'cancellation') then
          case when count(*) = 1 then '🎾 Court free' else '🎾 Courts free' end
      end as headline,
      array_agg(id order by id) as alert_ids
    from alerts group by member_id
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'chat_id', m.telegram_id,
    'text', format(E'<b>%s</b>\n\n%s', ms.headline,
      (select string_agg(line, E'\n' order by date, hour) from lines l where l.member_id = ms.member_id)),
    'alert_ids', ms.alert_ids
  ) order by ms.member_id), '[]')
  from messages ms join member m on m.id = ms.member_id
$$;

-- --- record_release -------------------------------------------------------

-- Called once `day` is open. Every slot the latest snapshot shows free on it is
-- a Release drop: each member watching it gets a release alert, skipping
-- members sent that slot in the last 30 minutes or with a pending alert for it.
-- Returns the messages and marks tonight's release done, so scans resume; an
-- alert whose send never gets reported is then retried by record_scan.
create function record_release(day date) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  alert_ids bigint[];
begin
  with releases as (
    insert into alert (member_id, court, date, hour, kind)
    select m, s.court, s.date, s.hour, 'release'
    from slot s
    cross join lateral watched_by(s.date, s.hour) m
    where s.date = day and s.status = 'free'
      and not sent_in_last_30_min(m, s.court, s.date, s.hour)
      and not exists (
        select from alert a
        where (a.member_id, a.court, a.date, a.hour) = (m, s.court, s.date, s.hour) and pending(a)
      )
    order by m, s.court, s.hour
    returning id
  )
  select array_agg(id) into alert_ids from releases;

  update marker set done_at = london_now()
  where (kind, for_date) = ('release', day) and done_at is null;

  return alert_messages(alert_ids);
end
$$;
