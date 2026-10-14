-- The 20:00 heads-up: once an evening, each member with watched hours free on
-- the day that opens at midnight gets one message listing them, without links.

-- From 20:00 London, claims today's heads_up marker for run_id and returns
-- {"for_date", "messages": [{"chat_id", "text"}]}, one message per member, for
-- the watched hours on window_end() + 1 that at least one court shows free now.
-- Returns null before 20:00 or once the marker is done. The marker is set done
-- by mark_heads_up_done once the sends are reported, so a run that dies before
-- that leaves them to the next scan; with nothing to send it is done at once.
create function heads_up_due(run_id text) returns jsonb
language plpgsql
set search_path = public, pg_catalog
as $$
declare
  today date := london_now()::date;
  messages jsonb;
begin
  if london_now()::time < '20:00' then
    return null;
  end if;
  insert into marker (kind, for_date, claimed_by, claimed_at)
  values ('heads_up', today, run_id, london_now())
  on conflict do nothing;
  if (select done_at from marker where (kind, for_date) = ('heads_up', today)) is not null then
    return null;
  end if;

  -- The same line format as alert_messages, with the courts unlinked.
  with free as (
    select m as member_id, s.date, s.hour, string_agg(format('C%s', s.court), ' ' order by s.court) as courts
    from slot s
    cross join lateral watched_by(s.date, s.hour) m
    where s.date = window_end() + 1 and s.status = 'free'
    group by m, s.date, s.hour
  ), lines as (
    select member_id, string_agg(format('%s %s:00  %s',
      to_char(date, 'Dy FMDD Mon'), lpad(hour::text, 2, '0'), courts), E'\n' order by date, hour) as lines
    from free group by member_id
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'chat_id', m.telegram_id,
    'text', format(E'<b>🌙 Opens at midnight</b>\n\n%s', l.lines)
  ) order by l.member_id), '[]')
  into messages
  from lines l join member m on m.id = l.member_id;

  if messages = '[]' then
    perform mark_heads_up_done(today);
  end if;
  return jsonb_build_object('for_date', today, 'messages', messages);
end
$$;

-- Called once the heads-ups for `day` are sent and reported, whatever the
-- outcome: a heads-up is never retried, since the release alert follows anyway.
create function mark_heads_up_done(day date) returns void
language sql
set search_path = public, pg_catalog
as $$
  update marker set done_at = london_now()
  where (kind, for_date) = ('heads_up', day) and done_at is null
$$;
