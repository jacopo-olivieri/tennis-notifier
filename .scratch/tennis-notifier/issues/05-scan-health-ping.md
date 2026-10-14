# 05: Scan health ping

**What to build:** the owner is told by Healthchecks.io (Telegram and email) when regular scans stop succeeding for 30 minutes, and not for transient one-court 520s. Spec: Health predicate, Health monitoring.

**Blocked by:** 03

**Status:** ready-for-agent

- [x] A pure `should_ping(scan_result, send_outcomes)`: true only if `record_scan` succeeded, all 3 courts were complete and no send returned 401; unit tests cover all complete, one court incomplete, a 401 present, and a 403 only (still pings)
- [x] The `scan` job pings the `scan` URL after the sends, only when `should_ping` is true
- [ ] HITL: the owner creates the Healthchecks.io `scan` check (cron-job.org schedule, Europe/London, 30 min grace), connects the Telegram and email integrations, and stores the ping URL as a GitHub secret (via `/wizard`)
- [ ] Live check: a deliberately broken parser run withholds the ping

## Comments

**2026-10-14:** Implemented in `notifier/health.py`, tested in `tests/test_health.py`, wired into `notifier/scan.py`. The HITL setup and the live check are still open.

- `should_ping(scan_result, send_outcomes)` takes `record_scan`'s result (it reads `all_complete`) and the HTTP status of each send. Only a 401 withholds the ping; a 403, a 429, a 5xx or no response (`None`) doesn't. In the job a failed `record_scan` raises before the predicate, so no ping is sent; the `None` case only exists to keep the predicate total.
- `ping("scan")` reads `HEALTHCHECKS_SCAN_URL`, so the GitHub secret must have exactly that name; `scan.yml` passes it through. With no URL set it prints "skipped" and carries on. A failed ping is only printed and doesn't fail the job, since Healthchecks treats it as a missed ping. Ticket 06 can call `ping("release")` with `HEALTHCHECKS_RELEASE_URL`.
- The ping comes before the existing `sys.exit` for failed courts. That exit never pings anyway, because a failed court means `all_complete` is false.
- When `heads_up_due()` lands (ticket 07), its send statuses must be added to `send_outcomes` before the ping.
