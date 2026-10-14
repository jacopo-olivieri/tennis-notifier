-- Delivery rules: the 30-minute rule, retries of unsent alerts, and members the
-- bot can't reach.
--
-- An alert is unsent while sent_at is null, and abandoned once it has failed 3
-- times. Only sent alerts count toward the 30-minute rule.

-- --- matching -------------------------------------------------------------

-- Whether member m was sent this slot (court c, date d, hour h) in the last 30
-- minutes, counting exactly 30 minutes ago.
create function sent_in_last_30_min(m bigint, c smallint, d date, h smallint) returns boolean
language sql stable
set search_path = public, pg_catalog
as $$
  select exists (
    select from alert
    where (member_id, court, date, hour) = (m, c, d, h)
      and sent_at >= london_now() - interval '30 minutes'
  )
$$;

-- Whether an alert is still to be delivered: unsent and not abandoned.
create function pending(a alert) returns boolean
language sql immutable
set search_path = pg_catalog
as $$
  select a.sent_at is null and a.failures < 3
$$;

-- --- formatting -----------------------------------------------------------

-- As before, plus the headline for a message mixing kinds, such as a
-- Cancellation with a retried release alert. Other single-kind headlines are
-- still to come.
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

-- --- reporting sends ------------------------------------------------------

-- A successful send also shows the member can be reached again. An alert
-- reported sent twice keeps its first sent_at, so the 30-minute rule doesn't move.
create or replace function mark_sent(alert_ids bigint[]) returns void
language sql
set search_path = public, pg_catalog
as $$
  update alert set sent_at = london_now() where id = any(alert_ids) and sent_at is null;
  update member set unreachable_since = null
  where id in (select member_id from alert where id = any(alert_ids));
$$;

-- http_status is null when the request never got a response. An alert abandoned
-- with a 403 (the member blocked the bot) marks its member unreachable; the
-- first such time is kept.
create or replace function mark_failed(alert_ids bigint[], http_status integer, error text) returns void
language sql
set search_path = public, pg_catalog
as $$
  with failed as (
    update alert set failures = failures + 1, last_error = concat_ws(' ', http_status, error)
    where id = any(alert_ids)
    returning member_id, failures
  )
  update member set unreachable_since = coalesce(unreachable_since, london_now())
  where http_status = 403 and id in (select member_id from failed where failures >= 3)
$$;

-- --- record_scan ----------------------------------------------------------

-- As before, with the delivery rules: a Cancellation skips members sent that
-- slot in the last 30 minutes or with a pending alert for it, and the messages
-- also carry retries of pending alerts whose slot a complete court still shows
-- free and that hasn't started. An alert that has never failed is left to its
-- sender for 2 minutes, so a send still in flight (from this job or another
-- producer) isn't doubled, and one whose sender died is still delivered.
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

  -- Retries read the alert table as it was before this statement, so they never
  -- include the cancellations it inserts.
  with cancellations as (
    insert into alert (member_id, court, date, hour, kind)
    select m, f.court, f.date, f.hour, 'cancellation'
    from jsonb_to_recordset(freed) as f(court smallint, date date, hour smallint)
    cross join lateral watched_by(f.date, f.hour) m
    where f.date <= window_end() and f.date + make_interval(hours => f.hour) > london_now()
      and not sent_in_last_30_min(m, f.court, f.date, f.hour)
      and not exists (
        select from alert a
        where (a.member_id, a.court, a.date, a.hour) = (m, f.court, f.date, f.hour) and pending(a)
      )
    returning id
  ), retries as (
    select a.id from alert a
    join slot s on (s.court, s.date, s.hour) = (a.court, a.date, a.hour)
    where pending(a) and a.court = any(complete) and s.status = 'free'
      and (a.failures > 0 or a.created_at <= london_now() - interval '2 minutes')
      and a.date + make_interval(hours => a.hour) > london_now()
      and not sent_in_last_30_min(a.member_id, a.court, a.date, a.hour)
  )
  select array_agg(id) into alert_ids
  from (select id from cancellations union all select id from retries) due;

  return jsonb_build_object(
    'all_complete', complete @> '{1,2,3}',
    'failed', failed,
    'messages', alert_messages(alert_ids)
  );
end
$$;
