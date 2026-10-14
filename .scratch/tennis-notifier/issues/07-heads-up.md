# 07: 20:00 heads-up

**What to build:** at about 20:00 London time, each Member with watched hours on the day that opens at midnight gets one `🌙 Opens at midnight` message listing those hours and the courts free on the grid now, with no links. Spec: `heads_up_due`, Rules (heads-up marker), Message format.

**Blocked by:** 03

**Status:** resolved

- [x] `heads_up_due()` returns nothing before 20:00; at or after 20:00 it claims the `heads_up` marker for today and returns Heads-ups for watched hours on today + 35 where at least one court shows free
- [x] It returns nothing once the marker is done; the marker is set done only after its sends are reported
- [x] Heads-up lines have no links; weekly and single-date watches (including dates not yet open) both qualify
- [x] The `scan` job calls it on every run after the alerts
- [x] SQL tests: 19:59 versus 20:00, only once per evening, a missed 20:00 run caught by a later scan, the BST→GMT day

## Comments

**2026-10-14:** Implemented in `supabase/migrations/20261014220000_heads_up.sql` and `notifier/scan.py` (`send_heads_up`). Tested in `tests/db/test_heads_up.py`. The spec's function table is updated to match.

- **Two departures from the spec's signature:**
  - `heads_up_due(run_id)` takes the run ID (`GITHUB_RUN_ID`), as `claim_release` does, so the marker records which run claimed it.
  - It returns `{for_date, messages}`, or null when nothing is due. The scan job sends the messages, then calls `mark_heads_up_done(for_date)`, which sets the marker done. That call is the "after its sends are reported" step.
- **A claimed marker that isn't done is served again.** If a run dies before `mark_heads_up_done`, the next scan resends the whole evening's heads-ups, so a member may get a duplicate. Scans are serialised by the `scan` concurrency group, so two live runs never share a claim.
- **Heads-ups aren't retried.** They have no `alert` rows, so `mark_sent` and `mark_failed` don't apply. A failed send is printed and dropped, and the release alert follows at midnight anyway. A 401 still withholds the `scan` ping.
- **If nothing qualifies at the first run after 20:00, the marker is done at once.** An hour that comes free later that evening gets no heads-up; the heads-up is a snapshot of the grid around 20:00. A run after midnight never sends the previous evening's heads-up, since the new day is before 20:00.
- **The BST→GMT test** pins the local clock, like the release tests. It checks that 25 Oct's heads-up targets Sun 29 Nov and fires at 20:00, not 19:59:59.
- **Left as judgement calls from the review:**
  - The line format is repeated from `alert_messages`. Sharing it would mean redefining `alert_messages` again.
  - The `run_id` expression is duplicated with `release.py`.
- **Smoke run** (Camden, Telegram and Healthchecks faked, against a scratch Postgres): the first scan at 20:03 sent one `🌙 Opens at midnight` DM and pinged. The second scan sent nothing.
- **Still to do:** apply the migration to the live Supabase and push.

**2026-10-14:** The migration was applied in the Supabase SQL editor (`mark_heads_up_done` answers 204 live), then pushed as 3c47964. The first live heads-up goes out with the next scan after the push, as a missed-20:00 catch-up.
