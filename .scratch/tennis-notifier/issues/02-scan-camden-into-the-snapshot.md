# 02: Scan Camden into the snapshot

**What to build:** a `scan` run reads all 3 courts' 6-week grids from Camden Active and stores every Slot in Supabase, logging each status change and each court's scan outcome. A court that doesn't scan completely leaves its stored slots untouched. This is the tracer bullet: migration, test harness, scraper, `record_scan` and a workflow that can be dispatched by hand. No alerts yet. Spec: Scraper module, Data model, The clock seam, `record_scan`, Testing Decisions seams 1–2.

**Blocked by:** None (can start immediately). The live demo needs 01.

**Status:** resolved

- [x] First migration: `member`, `watch`, `slot`, `slot_change`, `alert`, `scan_log`, `london_now()` (honours the `app.now` setting) and `window_end()`; no Supabase-only features
- [x] Test harness: pytest + psycopg against a plain Postgres; each test runs in a rolled-back transaction with a pinned clock; a CI job runs it on a `postgres:16` service container
- [x] CI fails if `now()`, `current_date`, `current_timestamp` or `localtime` appears in a migration outside `london_now()`
- [x] Scraper ported from the logger, stdlib only: pure `parse_week` and `next_week_form`, tested against the saved sample pages and a broken page that raises a parse error
- [x] `scan_court` reports the slots and the number of weeks parsed, or an error; `record_scan` decides completeness (all 6 weeks, and at least 50% of the court's previous slots)
- [x] `record_scan` upserts complete courts, keeps future slots that vanish (never deletes them), logs `slot_change` rows and one `scan_log` row per court; tests cover a 5-of-6-weeks court and a below-50% court being skipped while the others apply
- [x] The poller calls `record_scan` over Supabase's REST RPC with the service key
- [x] A `scan` workflow (`workflow_dispatch` only, own concurrency group) runs it; dispatched by hand, slot rows appear in Supabase (once 01 is done)

## Comments

**2026-10-14:** Done in 9d3bd2d. Migration applied by hand in the Supabase SQL editor; the first dispatched `scan` ([run 38539654164](https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/38539654164)) stored 1,098 slots (366 per court, 14 Oct–24 Nov) and three `ok` scan_log rows.

- Courts run 10 hours a day (08–17) until the clocks change on 25 Oct, then 9, then 8 from 2 Nov, so a court's slot count varies with the season. The 50% rule copes, but don't expect a fixed 420.
- Beyond the checklist: RLS on all tables, execute only for `service_role`, and default privileges so later migrations' functions and tables follow suit without their own grants.
- A court whose data `record_scan` can't store is rolled back on its own, logged as `not recorded: …` and returned in `failed`; `scan.py` then fails the job. Only network and parse errors are caught in the scraper; any other exception fails the job.
