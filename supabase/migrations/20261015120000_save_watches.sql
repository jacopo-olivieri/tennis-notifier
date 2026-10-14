-- Saving watches: a member's batch of added and removed hours, the new-watch
-- alert for the slots already free on the added ones, and the availability the
-- site shows.

-- --- availability ---------------------------------------------------------

-- Per date and hour that hasn't started, from the snapshot: the courts free and
-- a status. 'no session' means no court runs then (e.g. after dusk), 'not open'
-- a day after window_end(), whatever its grid shows. Hours are those any court
-- runs on some day, so an hour missing on one day is 'no session' there.
-- security_invoker: a view otherwise reads as its owner, getting round RLS.
create view availability with (security_invoker = true) as
with upcoming as (
  select * from slot where date + make_interval(hours => hour) > london_now()
)
select d.date, h.hour,
  coalesce(array_agg(s.court order by s.court) filter (where s.status = 'free' and d.date <= window_end()), '{}')
    as free_courts,
  case
    when count(s.court) = 0 then 'no session'
    when d.date > window_end() then 'not open'
    when bool_or(s.status = 'free') then 'free'
    else 'booked'
  end as status
from (select distinct date from upcoming) d
cross join (select distinct hour from upcoming) h
left join upcoming s on (s.date, s.hour) = (d.date, h.hour)
where d.date + make_interval(hours => h.hour) > london_now()
group by d.date, h.hour;

do $$
begin
  if exists (select from pg_roles where rolname = 'anon') then
    revoke all on availability from anon, authenticated;
  end if;
end
$$;

-- --- formatting -----------------------------------------------------------

-- As before, plus the new-watch alert: with `added` (the hours added in that
-- save, as one line) the headline is "Free now for your new watches" with that
-- line under it. A new-watch alert retried by a later scan is just "Free now".
drop function alert_messages(bigint[]);
create function alert_messages(ids bigint[], added text default null) returns jsonb
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
        when added is not null then '🎾 Free now for your new watches'
        when count(distinct kind) > 1 or bool_and(kind = 'new_watch') then '🎾 Free now'
        when bool_and(kind = 'release') then '🎾 Just released'
        when bool_and(kind = 'cancellation') then
          case when count(*) = 1 then '🎾 Court free' else '🎾 Courts free' end
      end as headline,
      array_agg(id order by id) as alert_ids
    from alerts group by member_id
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'chat_id', m.telegram_id,
    'text', format(E'<b>%s</b>%s\n\n%s', ms.headline, E'\n' || added,
      (select string_agg(line, E'\n' order by date, hour) from lines l where l.member_id = ms.member_id)),
    'alert_ids', ms.alert_ids
  ) order by ms.member_id), '[]')
  from messages ms join member m on m.id = ms.member_id
$$;

-- --- save_watches ---------------------------------------------------------

-- Applies one save: `removed` then `added`, each a list of {"weekday", "hour"}
-- (ISO weekday, Mon = 1) or {"date", "hour"}. An hour in both stays as it
-- was, an hour already watched isn't added twice, and a single-date hour that
-- has started isn't added at all. Returns the new-watch message {"chat_id",
-- "text", "alert_ids"} for the slots free now on the hours this save added, or
-- null. It ignores the 30-minute rule, since the member just asked, but its
-- alerts count toward it once sent. A slot with an alert still pending is left
-- to that alert's retry, so it is never listed twice.
create function save_watches(member_id bigint, added jsonb, removed jsonb) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
#variable_conflict use_column
declare
  m bigint := save_watches.member_id;
  added_line text;
  alert_ids bigint[];
begin
  delete from watch w
  using jsonb_to_recordset(removed) r(weekday smallint, date date, hour smallint)
  where w.member_id = m and w.hour = r.hour
    and w.weekday is not distinct from r.weekday and w.date is not distinct from r.date
    and not exists (
      select from jsonb_to_recordset(added) a(weekday smallint, date date, hour smallint)
      where (a.weekday, a.date, a.hour) is not distinct from (r.weekday, r.date, r.hour)
    );

  with new as (
    insert into watch (member_id, weekday, date, hour)
    select distinct m, a.weekday, a.date, a.hour
    from jsonb_to_recordset(added) a(weekday smallint, date date, hour smallint)
    where a.date is null or a.date + make_interval(hours => a.hour) > london_now()
    on conflict do nothing
    returning weekday, date, hour
  ), new_alerts as (
    insert into alert (member_id, court, date, hour, kind)
    select m, s.court, s.date, s.hour, 'new_watch'
    from slot s
    where s.status = 'free' and s.date <= window_end()
      and s.date + make_interval(hours => s.hour) > london_now()
      and exists (
        select from new w where w.hour = s.hour and (w.date = s.date or w.weekday = extract(isodow from s.date))
      )
      and not exists (
        select from alert a where (a.member_id, a.court, a.date, a.hour) = (m, s.court, s.date, s.hour) and pending(a)
      )
    order by s.date, s.hour, s.court
    returning id
  )
  select
    -- Weekly hours first, by weekday; 2024-01-01 was a Monday.
    (select string_agg(case
        when weekday is not null then format('Weekly %s %s:00', to_char(date '2024-01-01' + weekday - 1, 'Dy'), lpad(hour::text, 2, '0'))
        else format('%s %s:00', to_char(date, 'Dy FMDD Mon'), lpad(hour::text, 2, '0'))
      end, ' · ' order by weekday, date, hour) from new),
    (select array_agg(id order by id) from new_alerts)
  into added_line, alert_ids;

  return alert_messages(alert_ids, added_line)->0;
end
$$;

-- --- the site's state -----------------------------------------------------

-- What GET /state returns for a signed-in member, or null once they've been
-- removed: the member, their watches, availability for 7 weeks from today,
-- when the bot last failed to reach them, the last successful check of any
-- court and the last bookable day.
create or replace function member_state(member_id bigint) returns jsonb
language sql stable
set search_path = public, pg_catalog
as $$
  select jsonb_build_object(
    'member', jsonb_build_object('first_name', m.first_name, 'username', m.username, 'is_owner', m.is_owner),
    'watches', coalesce((
      select jsonb_agg(jsonb_build_object('weekday', w.weekday, 'date', w.date, 'hour', w.hour)
        order by w.weekday, w.date, w.hour)
      from watch w where w.member_id = m.id
    ), '[]'),
    'availability', coalesce((
      select jsonb_agg(to_jsonb(a) order by a.date, a.hour)
      from availability a where a.date < london_now()::date + 49
    ), '[]'),
    'unreachable_since', m.unreachable_since,
    'last_check', (select max(at) from scan_log where ok),
    'window_end', window_end()
  )
  from member m
  where m.id = member_state.member_id
$$;
