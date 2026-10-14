# 06: Midnight release

**What to build:** at midnight London time, every Member with a Watch on the newly opened day gets a `🎾 Just released` DM within seconds of it opening, regular scans stand aside while that happens, and the owner is alerted if a release doesn't complete. Spec: Architecture (release workflow), `claim_release` / `release_claim_held` / `record_release`, Poller orchestration (release job), Further Notes (verify the probe).

**Blocked by:** 03

**Status:** ready-for-agent

- [x] `claim_release(day, run_id)` lets exactly one run hold tonight's claim; `release_claim_held()` is true until `done_at` is set or 00:15 London, whichever comes first; the `scan` job exits at once while it's true
- [x] `record_release(day)` returns release alerts for every free slot on that day matching a Watch, from the latest snapshot, and sets `done_at`
- [x] Clock-boundary SQL tests: a not-open slot entering the window at 00:00:10 with its status unchanged gives nothing from `record_scan` but is alerted by `record_release`; the claim lapses at 00:15; the 25 Oct 2026 BST→GMT night behaves
- [x] A `release` workflow (own concurrency group): claim (exit if not held), sleep to 23:59:30, probe the releasing day every ~10 s, then `record_release`, send, report, and ping the Healthchecks `release` URL
- [x] Before relying on it, the `book.aspx` probe is confirmed to tell an open day from one not yet open; if it can't, the job falls back to calling `record_release` at 00:00:15. The outcome is recorded on this ticket
- [ ] HITL: the owner creates the `release` check (daily 00:00 Europe/London, 20 min grace) and stores its ping URL as a GitHub secret

## Comments

**2026-10-14:** Implemented in `supabase/migrations/20261014200000_midnight_release.sql`, `notifier/release.py` and `.github/workflows/release.yml`; tested in `tests/db/test_release.py`. The `scan` job now exits at once while `release_claim_held()` is true. The HITL step is still open: the owner runs `scripts/healthchecks.sh release`, which now sets up the `release` check and the `HEALTHCHECKS_RELEASE_URL` secret.

- **Probe outcome: it works, so the job relies on it.** Run live today with a session cookie fetched first, court 1 showed 7 open hours on 17 Nov (already bookable) and none on 18 Nov (opens tonight). The logger's `data/release_bursts.jsonl` shows the same probe flipping from refused to open on 7 nights in a row, between 23:59:43 and 00:00:02. The platform note's signed-out test, where every slot redirected to the detail page, skipped the cookie. A slot that is booked also redirects to the detail page, so the job probes 3 hours (08:00, 11:00, 14:00) on court 1 and treats any one that takes a booking as the day being open. As a safety net, if the probe hasn't seen the day open by 00:00:15, the job calls `record_release` anyway.
- **Claims are taken only from 23:30 to 00:15** (`release_due`). Without this, a `release` dispatched by hand in the daytime would claim tomorrow night's release and stop the scans until midnight. As a result, the release can't be tried out by a manual daytime dispatch; it's checked live on the first night (ticket 14).
- `record_release` applies the same 30-minute and pending-alert checks as `record_scan`, so a second call adds nothing. It may run a few seconds before midnight, since releases sometimes land early. The Healthchecks ping still waits until 00:00:01, because a ping before the check's 00:00 schedule would count for the previous night and raise a false alarm at 00:20. A 401 on any send withholds the ping, as for scans (`health.bot_token_ok`).
- The run ID is `GITHUB_RUN_ID`, so a GitHub re-run keeps its claim.
- **Known gaps, left as the spec has them:**
  - The 23:50 dispatch queues behind the 23:45 one in the `release` concurrency group. It only helps if the first run never started or died before claiming. If the first run claims and then dies, nothing takes over: the scans resume at 00:15 and the `release` check alarms.
  - A release alert whose send fails is retried by `record_scan` only once the claim has ended. It is then sent under the `🎾 Free now` or `🎾 Just released` headline, which can be up to about 15 minutes late overnight.
  - `record_release` and `record_scan` both carry the alert guard (30-minute rule plus pending). Folding it into one predicate would mean rewriting `record_scan` again.
- The Python side (`releasing_day`, the midnight sleep and the probe rounds) has no unit tests, by the spec's choice: it's observed live. A scratch smoke run with Camden and Telegram faked confirmed the following: one claim, a `🎾 Just released` DM reported as sent, the ping after 00:00:01, a second run adding nothing, and a scan skipped while the claim is open.
