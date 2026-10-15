-- Daily housekeeping, so the free database never fills up. pg_cron calls
-- housekeep() at 02:00 UTC; the job is scheduled by hand (see the runbook), not
-- here, so CI's plain Postgres needs no pg_cron.

-- Deletes single-date watches and slots whose hour has started, invites past
-- their expiry (used, revoked or not), and alert, slot_change and scan_log rows
-- older than 30 days. Weekly watches, members and markers are kept.
create function housekeep() returns void
language sql
set search_path = public, pg_catalog
as $$
  delete from watch where date + make_interval(hours => hour) <= london_now();
  delete from slot where date + make_interval(hours => hour) <= london_now();
  delete from invite where expires_at <= london_now();
  delete from alert where created_at < london_now() - interval '30 days';
  delete from slot_change where at < london_now() - interval '30 days';
  delete from scan_log where at < london_now() - interval '30 days';
$$;
