# When to alert and how often to check

Type: grilling
Mode: HITL
Status: resolved
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

## Answer

Decided with the owner on 2026-10-12, using the data from [Observe a week of releases and cancellations](01-observe-releases-and-cancellations.md). Terms follow `GLOSSARY.md`; "Cancellation" keeps its name but now covers checkout holds expiring.

**What triggers an alert**
- **Release drop:** every slot matching a watch on the newly opened day, alerted the moment it opens.
- **Cancellation:** any booked → free change on a matching slot that hasn't started yet. There is no near-start cutoff for now; adding one later is cheap.
- **New watch:** one alert straight away, listing the matching slots that are free right now.
- **No repeats within 30 minutes:** the same slot isn't alerted to the same member again in that time. This absorbs the flipping while a slot is held, and still catches a hold expiring ~45 min later. A 60-minute window was rejected because it would suppress that second chance after a midnight race.
- **Grouping:** one message per member per check, listing every matching slot grouped by date and time, each with a booking link.

**Heads-up**
- Sent at ~20:00 London time on any day whose midnight release has slots matching the member's watch. Weekends and weekdays alike, since weekday 08:00s are sometimes taken at ~00:05.
- It says these slots *should* open, because hours the venue blocks before release can't be known in advance.
- The release alert still follows at midnight.

**Checking schedule**
- **Full scan:** every 5 min from 07:00 to 23:00 and every 15 min overnight, about 230 scans a day. Freed slots stay free for a median of ~6 h, and only 1 of 37 was re-taken within 10 min, so 5 min loses almost nothing.
- **Release burst:** from 23:59:30, check only the releasing day every ~10 s until it opens, alert at once, then return to the normal schedule. Weekend mornings are gone within 1–2.5 min, so the next 5-minute tick would be too late.

**What this requires of [Choose the hosting architecture](06-hosting-architecture.md):** a trigger that fires to within seconds just before midnight, every 5 min otherwise, and at 20:00 for the heads-up. GitHub's `schedule` trigger can't do this; an external cron calling `workflow_dispatch` could.
