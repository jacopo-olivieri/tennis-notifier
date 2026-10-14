# 05: Scan health ping

**What to build:** the owner is told by Healthchecks.io (Telegram and email) when regular scans stop succeeding for 30 minutes, and not for transient one-court 520s. Spec: Health predicate, Health monitoring.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] A pure `should_ping(scan_result, send_outcomes)`: true only if `record_scan` succeeded, all 3 courts were complete and no send returned 401; unit tests cover all complete, one court incomplete, a 401 present, and a 403 only (still pings)
- [ ] The `scan` job pings the `scan` URL after the sends, only when `should_ping` is true
- [ ] HITL: the owner creates the Healthchecks.io `scan` check (cron-job.org schedule, Europe/London, 30 min grace), connects the Telegram and email integrations, and stores the ping URL as a GitHub secret (via `/wizard`)
- [ ] Live check: a deliberately broken parser run withholds the ping
