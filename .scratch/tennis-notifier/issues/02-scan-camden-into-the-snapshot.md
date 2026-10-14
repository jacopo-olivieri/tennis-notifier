# 02: Scan Camden into the snapshot

**What to build:** a `scan` run reads all 3 courts' 6-week grids from Camden Active and stores every Slot in Supabase, logging each status change and each court's scan outcome. A court that doesn't scan completely leaves its stored slots untouched. This is the tracer bullet: migration, test harness, scraper, `record_scan` and a workflow that can be dispatched by hand. No alerts yet. Spec: Scraper module, Data model, The clock seam, `record_scan`, Testing Decisions seams 1–2.

**Blocked by:** None (can start immediately). The live demo needs 01.

**Status:** ready-for-agent

- [ ] First migration: `member`, `watch`, `slot`, `slot_change`, `alert`, `scan_log`, `london_now()` (honours the `app.now` setting) and `window_end()`; no Supabase-only features
- [ ] Test harness: pytest + psycopg against a plain Postgres; each test runs in a rolled-back transaction with a pinned clock; a CI job runs it on a `postgres:16` service container
- [ ] CI fails if `now()`, `current_date`, `current_timestamp` or `localtime` appears in a migration outside `london_now()`
- [ ] Scraper ported from the logger, stdlib only: pure `parse_week` and `next_week_form`, tested against the saved sample pages and a broken page that raises a parse error
- [ ] `scan_court` reports the slots and the number of weeks parsed, or an error; `record_scan` decides completeness (all 6 weeks, and at least 50% of the court's previous slots)
- [ ] `record_scan` upserts complete courts, keeps future slots that vanish (never deletes them), logs `slot_change` rows and one `scan_log` row per court; tests cover a 5-of-6-weeks court and a below-50% court being skipped while the others apply
- [ ] The poller calls `record_scan` over Supabase's REST RPC with the service key
- [ ] A `scan` workflow (`workflow_dispatch` only, own concurrency group) runs it; dispatched by hand, slot rows appear in Supabase (once 01 is done)
