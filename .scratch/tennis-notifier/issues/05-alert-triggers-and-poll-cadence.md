# When to alert and how often to check

Type: grilling
Mode: HITL
Status: open
Blocked by: 01
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Given the observed release time and cancellation rate, what exactly triggers an alert, and what checking schedule catches it fast enough without hammering the site?

Sub-questions:
- Should release drops be detected by polling right after release, or should there also be a reminder before release ("Sat 18:00 opens at 00:00 tonight")?
- Is polling for cancellations worth it at all if they turn out to be very rare?
- How should alerts be grouped when one release matches many slots?

## Comments

- 2026-10-04: Levers against GitHub Actions' 5-min cron floor, to weigh once the observation data is in:
  - **Release drops:** a job started just before the known release time can poll only the newly releasing day every 20–30s for 10–15 min. A single job may run up to 6h, so the cron floor doesn't apply within it.
  - **Cancellations:** probe only the watched slots via book.aspx (~1s each; free → login redirect) rather than the ~3–4 min full grid scan, so checks can run every 1–2 min.
  - **Continuous loop:** an always-on loop is likely outside GitHub Actions' acceptable use, which points to the Oracle free VM or Cloudflare Workers' 1-min cron (see the hosting research).
  - **Deciding fact:** how long freed slots stay free, from `data/events.jsonl`. Note that 5-min scans can't see slots that survive under ~5 min.
