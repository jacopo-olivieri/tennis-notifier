-- Cancellation alerts: record_scan returns ready-to-send Telegram messages for
-- watched slots that went booked -> free, and the poller reports each send.
--
-- The shared pipeline every producer reuses: watched_by() matches a slot to
-- Watches, and alert_messages() groups alert rows by member and formats them.

-- --- matching -------------------------------------------------------------

-- The members with a Watch on this hour: weekly (same ISO weekday) or single-date.
create function watched_by(d date, h smallint) returns setof bigint
language sql stable
set search_path = public, pg_catalog
as $$
  select distinct member_id from watch
  where hour = h and (date = d or weekday = extract(isodow from d))
$$;

-- --- formatting -----------------------------------------------------------

-- A court's detail page on Camden Active; the same pages as COURTS in notifier/scraper.py.
create function court_page(court smallint) returns text
language sql immutable
set search_path = pg_catalog
as $$
  select 'https://camdenactive.camden.gov.uk/courses/detail/' || case court
    when 1 then '171/lincoln-s-inn-fields-tennis-court-1/'
    when 2 then '176/lincoln-s-inn-fields-tennis-court-2/'
    when 3 then '177/lincoln-s-inn-fields-tennis-court-3/'
  end
$$;

-- One Telegram message per member for these alerts, as
-- [{"chat_id", "text", "alert_ids"}], ordered by member. The text is HTML:
-- a bold headline, a blank line, then one line per date and hour in
-- date-then-hour order, like `Wed 14 Oct 10:00  C1 C3`, each court linked.
create function alert_messages(ids bigint[]) returns jsonb
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
      case when bool_and(kind = 'cancellation') then
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

-- --- reporting sends ------------------------------------------------------

create function mark_sent(alert_ids bigint[]) returns void
language sql
set search_path = public, pg_catalog
as $$
  update alert set sent_at = london_now() where id = any(alert_ids)
$$;

-- http_status is null when the request never got a response.
create function mark_failed(alert_ids bigint[], http_status integer, error text) returns void
language sql
set search_path = public, pg_catalog
as $$
  update alert set failures = failures + 1, last_error = concat_ws(' ', http_status, error)
  where id = any(alert_ids)
$$;

-- --- record_scan ----------------------------------------------------------

-- As before, plus: every slot a complete court shows going booked -> free is a
-- Cancellation if it is within the booking window and hasn't started. Each
-- member watching it gets an alert row, and the result carries the messages.
create or replace function record_scan(courts jsonb) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  c jsonb;
  n smallint;
  scanned integer;
  previous integer;
  problem text;
  court_freed jsonb;
  freed jsonb := '[]';
  complete smallint[] := '{}';
  failed jsonb := '[]';
  alert_ids bigint[];
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

      -- Every part reads the snapshot as it was before this statement. Slots missing
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
        returning court, date, hour, from_status, to_status
      ), upsert as (
        insert into slot as sl (court, date, hour, status, status_since, last_seen_at)
        select n, date, hour, status, london_now(), london_now() from scanned
        on conflict (court, date, hour) do update set
          status = excluded.status,
          status_since = case when sl.status = excluded.status then sl.status_since else excluded.status_since end,
          last_seen_at = excluded.last_seen_at
      )
      select coalesce(jsonb_agg(jsonb_build_object('court', court, 'date', date, 'hour', hour)), '[]')
      into court_freed
      from changes where (from_status, to_status) = ('booked', 'free');
      insert into scan_log (at, court, ok, slots, error) values (london_now(), n, true, scanned, null);
      complete := complete || n;
      freed := freed || court_freed;
    exception when others then
      -- The block's own work is rolled back; log the court as failed instead.
      insert into scan_log (at, court, ok, slots, error)
      values (london_now(), n, false, scanned, 'not recorded: ' || sqlerrm);
      failed := failed || jsonb_build_object('court', n, 'error', sqlerrm);
    end;
  end loop;

  with cancellations as (
    insert into alert (member_id, court, date, hour, kind)
    select m, f.court, f.date, f.hour, 'cancellation'
    from jsonb_to_recordset(freed) as f(court smallint, date date, hour smallint)
    cross join lateral watched_by(f.date, f.hour) m
    where f.date <= window_end() and f.date + make_interval(hours => f.hour) > london_now()
    returning id
  )
  select array_agg(id) into alert_ids from cancellations;

  return jsonb_build_object(
    'all_complete', complete @> '{1,2,3}',
    'failed', failed,
    'messages', alert_messages(alert_ids)
  );
end
$$;
