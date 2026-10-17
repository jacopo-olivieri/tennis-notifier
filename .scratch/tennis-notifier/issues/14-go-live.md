# 14: Go live

**What to build:** the notifier runs on its real schedule, the old logger is retired, and the owner has watched it work end to end, including the first midnight release. HITL: the agent prepares a `/wizard` for the dashboard steps. Spec: Deploy and operate (runbook), steps 1 and 3–8.

**Blocked by:** 01, 05, 06, 07, 10, 11, 12, 13

**Status:** ready-for-agent

**Type:** HITL

- [x] GitHub Pages serves the site and BotFather `/setdomain` is set to its domain
- [x] A fine-grained PAT (this repo, Actions write only, maximum expiry) is stored in cron-job.org
- [x] cron-job.org dispatches `scan` every 5 min 07:00–23:00 and every 15 min 23:00–07:00, and `release` at 23:45 and 23:50, all Europe/London
- [x] The `observe` workflow is disabled and removed, and `data/` commits stop
- [ ] Smoke test passes: a manual `scan` stores slots and turns the `scan` check green; owner login, an invite redeemed from a second Telegram account, and a saved watch delivers the new-watch DM
- [x] The first midnight release is watched live and the `release` check goes green
- [x] The runbook's PAT-rotation step is in place

## Comments

**2026-10-15:** Wizard ready. Still to do by hand: push main, then run `scripts/go_live.sh` in a terminal.

- **Already done:** Pages and BotFather `/setdomain` (ticket 08). `observe` was disabled on GitHub on 2026-10-12; `observe.yml` is deleted in this commit (tick the box once it's pushed), so nothing commits to `data/`. `logger/` and `data/` stay as the record the decision docs cite.
- **`scripts/cron_jobs.py`** creates the cron-job.org jobs through its REST API instead of the dashboard, with tests in `tests/test_cron_jobs.py`. There are three jobs, all Europe/London, each a POST of `workflow_dispatch` on main with the PAT:
  - `scan (day)`: hours 07–22, every 5 min.
  - `scan (night)`: hours 23 and 00–06, every 15 min.
  - `release`: 23:45 and 23:50.
  It matches existing jobs by title, so a re-run updates them in place instead of adding duplicates.
- **`scripts/go_live.sh`**, 6 stages:
  1. Preflight: main pushed, `observe.yml` gone from GitHub, site answering 200.
  2. Make the PAT. The wizard checks it against the API. It's kept only in cron-job.org; its expiry goes in `.env` as `DISPATCH_PAT_EXPIRES`.
  3. Dispatch `scan` with the PAT, the same request cron-job.org sends. The wizard waits for the run and prints the court, `record_scan` and ping lines.
  4. Paste a cron-job.org API key (saved in `.env` as `CRONJOB_API_KEY`), then run `cron_jobs.py`.
  5. Owner login, an invite redeemed from a second account, and the new-watch DM.
  6. What to watch for at tonight's release.
- **PAT rotation:** `scripts/go_live.sh rotate` runs only the preflight, PAT and cron-job.org stages, then points at the old token to delete. The spec's runbook steps 6 and 8 now name the scripts.
- **From the review:** fixed a wizard exit when a run's log had no court lines, the release text (the 23:50 run queues behind the 23:45 one and exits after midnight), re-recording the old expiry on `rotate`, and the spec's Secrets table and Testing Decisions now list the API key and `cron_jobs.py`. Left: the schedule is written both in `job_specs` and in the wizard's notes; the repo slug is hard-coded in `cron_jobs.py`.

**2026-10-16:** The owner ran `scripts/go_live.sh`.
- **Token:** the fine-grained token expires 2027-10-15.
- **Scan smoke test:** a dispatch with the token ([run 38820527559](https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/38820527559)) had 3 complete courts and logged `ping: 200`. The scan check in Healthchecks is named `tennis-notifier`; its URL matches `HEALTHCHECKS_SCAN_URL`.
- **cron-job.org jobs:** 8655384 scan (day), 8655385 scan (night) and 8655386 release, all enabled in Europe/London. The first scheduled scan at 00:15 ([run 38822489997](https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/38822489997)) had 3 complete courts and logged `ping: 200`.
- **Release:** the jobs were created after 23:50, so the night of 15–16 Oct had no release run, and the `release` check alarms for it. The first live release is the night of 16–17 Oct.
- **Still open:** confirm the members smoke test (stage 5), and watch that release.

**2026-10-17:** First live release, night of 16–17 Oct.
- The 23:45 run ([38977627183](https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/38977627183)) claimed the release of 2026-11-20. Its probe saw the day open at 00:00:06, `record_release` returned 0 messages because nobody watches those hours, and it logged `ping: 200`.
- The 23:50 run ([38978102606](https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/38978102606)) queued, then logged "not claimed … exiting". Scheduled scans carried on through the morning.
- Still open: confirm the members smoke test (stage 5).
