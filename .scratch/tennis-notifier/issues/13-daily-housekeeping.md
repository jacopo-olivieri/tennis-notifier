# 13: Daily housekeeping

**What to build:** old data is cleared daily, so the free database never fills up and past single-date watches disappear quietly. Spec: `housekeep()`, Deploy and operate step 2 (pg_cron).

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] A plain `housekeep()` function deletes past single-date watches, past slots, expired invites, and `alert`, `slot_change` and `scan_log` rows older than 30 days
- [ ] SQL tests with a pinned clock show it deletes exactly that and nothing still current
- [ ] HITL: `pg_cron` schedules `housekeep()` at 02:00 UTC in the Supabase project (the job lives in the runbook, not the migration)
