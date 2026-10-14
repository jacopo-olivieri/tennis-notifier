# 14: Go live

**What to build:** the notifier runs on its real schedule, the old logger is retired, and the owner has watched it work end to end, including the first midnight release. HITL: the agent prepares a `/wizard` for the dashboard steps. Spec: Deploy and operate (runbook), steps 1 and 3–8.

**Blocked by:** 01, 05, 06, 07, 10, 11, 12, 13

**Status:** ready-for-agent

**Type:** HITL

- [ ] GitHub Pages serves the site and BotFather `/setdomain` is set to its domain
- [ ] A fine-grained PAT (this repo, Actions write only, maximum expiry) is stored in cron-job.org
- [ ] cron-job.org dispatches `scan` every 5 min 07:00–23:00 and every 15 min 23:00–07:00, and `release` at 23:45 and 23:50, all Europe/London
- [ ] The `observe` workflow is disabled and removed, and `data/` commits stop
- [ ] Smoke test passes: a manual `scan` stores slots and turns the `scan` check green; owner login, an invite redeemed from a second Telegram account, and a saved watch delivers the new-watch DM
- [ ] The first midnight release is watched live and the `release` check goes green
- [ ] The runbook's PAT-rotation step is in place
