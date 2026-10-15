# 13: Daily housekeeping

**What to build:** old data is cleared daily, so the free database never fills up and past single-date watches disappear quietly. Spec: `housekeep()`, Deploy and operate step 2 (pg_cron).

**Blocked by:** 03

**Status:** ready-for-agent

- [x] A plain `housekeep()` function deletes past single-date watches, past slots, expired invites, and `alert`, `slot_change` and `scan_log` rows older than 30 days
- [x] SQL tests with a pinned clock show it deletes exactly that and nothing still current
- [ ] HITL: `pg_cron` schedules `housekeep()` at 02:00 UTC in the Supabase project (the job lives in the runbook, not the migration)

## Comments

**2026-10-15:** Implemented. Still to do by hand:
1. Apply `supabase/migrations/20261016000000_housekeep.sql` in the Supabase SQL editor.
2. Enable `pg_cron` (Database → Extensions), then run `select cron.schedule('housekeep', '0 2 * * *', 'select housekeep()');`.
3. Run `select housekeep();` once by hand and check `cron.job_run_details` after the first night.

- **SQL** (new migration, with 7 tests in `tests/db/test_housekeep.py` and a grant test in `tests/db/test_grants.py`):
  - "Past" means the same as everywhere else: a single-date watch or slot goes once its hour has started (`date + hour <= london_now()`), so earlier hours today go too.
  - An invite goes once `expires_at <= london_now()`, the same line `login` uses. That includes used and revoked invites, since nothing reads them after expiry.
  - `alert`, `slot_change` and `scan_log` rows go when they are more than 30 days old. A row exactly 30 days old stays.
  - Weekly watches, members and `marker` rows are never touched. `marker` grows by two rows a night, which is too little to matter.
  - Only `service_role` can call it, like every other function. pg_cron runs it as `postgres`.
- **Spec changes:** the runbook has the exact `cron.schedule` call. Its time note was backwards: 02:00 UTC is 03:00 London in summer and 02:00 in winter.
