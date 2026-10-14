# 06: Midnight release

**What to build:** at midnight London time, every Member with a Watch on the newly opened day gets a `🎾 Just released` DM within seconds of it opening, regular scans stand aside while that happens, and the owner is alerted if a release doesn't complete. Spec: Architecture (release workflow), `claim_release` / `release_claim_held` / `record_release`, Poller orchestration (release job), Further Notes (verify the probe).

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] `claim_release(day, run_id)` lets exactly one run hold tonight's claim; `release_claim_held()` is true until `done_at` is set or 00:15 London, whichever comes first; the `scan` job exits at once while it's true
- [ ] `record_release(day)` returns release alerts for every free slot on that day matching a Watch, from the latest snapshot, and sets `done_at`
- [ ] Clock-boundary SQL tests: a not-open slot entering the window at 00:00:10 with its status unchanged gives nothing from `record_scan` but is alerted by `record_release`; the claim lapses at 00:15; the 25 Oct 2026 BST→GMT night behaves
- [ ] A `release` workflow (own concurrency group): claim (exit if not held), sleep to 23:59:30, probe the releasing day every ~10 s, then `record_release`, send, report, and ping the Healthchecks `release` URL
- [ ] Before relying on it, the `book.aspx` probe is confirmed to tell an open day from one not yet open; if it can't, the job falls back to calling `record_release` at 00:00:15. The outcome is recorded on this ticket
- [ ] HITL: the owner creates the `release` check (daily 00:00 Europe/London, 20 min grace) and stores its ping URL as a GitHub secret
