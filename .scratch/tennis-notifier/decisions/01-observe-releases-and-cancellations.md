# Observe a week of releases and cancellations

Type: task
Mode: AFK
Status: resolved
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

At what time of day does a new day become bookable, and how often do booked slots become free again?

Run a temporary logger for about 7 days. It should take a snapshot of all 3 courts every 30–60 minutes, and also probe the `book.aspx` redirect for the first date past the window at several times: around 00:00, 06:00, 07:00 and 08:00. Record every booked → free change and every new date that appears. The logger may run on the owner's Mac temporarily, since it's an experiment and not the product. Running it on a cloud host instead would also test reachability.

The answer should record: the release time (or that it's continuous), the number of cancellations per week with their timing, and where the raw log lives.

See [Camden Active booking platform](../../../docs/research/camden_active_platform.md) for the scraping mechanics.

## Comments

- 2026-10-04: Logger built at `logger/observe.py`, running from `.github/workflows/observe.yml` every 15 min until 2026-10-12. Each run checks book.aspx for 07:00–21:00 on court 1 for days today+33..+36 (`data/probes.jsonl`). At most hourly it scans the full grid of all 3 courts and logs every slot change to `data/events.jsonl`. First local run: last bookable day 2026-11-07 (today+34), 1158 slots, 482 free, probe ~1 min, scan ~3 min. Note: today+34 already had some booked hours at first sight, so a day's release has to be judged hour by hour.
- 2026-10-04: Cadence raised to every 5 min (GitHub's minimum), with a full scan on every run. Hourly scans would miss a slot freed and re-booked within the hour, undercounting the cancellations we're trying to measure. Probes trimmed to days today+34 and +35 to keep the request load similar. Also watch how late or how often GitHub's scheduler runs, since that feeds [Choose the hosting architecture](06-hosting-architecture.md).
- 2026-10-05 (interim, ~15h in):
  - **GitHub's scheduler is heavily throttled.** Only 4 scheduled runs in ~13h, roughly every 3h, instead of every 5 min. All 6 runs succeeded with no blocking. This is a big data point for [Choose the hosting architecture](06-hosting-architecture.md): GitHub's `schedule` cannot be the trigger for anything time-sensitive.
  - **Release looks like midnight.** 2026-11-08 was refused at 21:01 and open at 00:01 on 10-05, i.e. today+34 opens at a day change between 21:01 and 00:01.
  - **The release race is very fast.** By 00:01:23, court 1 on 11-08 already had 09:00–14:00 booked except 12:00, and court 2 had 11:00–12:00 booked. Probably booked within ~1 min of release, unless the release came earlier than midnight.
  - **No cancellations seen yet** (no booked → free). Only 6 scans so far, so this is weak evidence.
  - **Fix:** added a release-burst mode, so a run starting 23:50–00:15 London watches the releasing day on all courts every ~20s (`data/release_bursts.jsonl`). A reliable trigger is still needed: an external cron calling `workflow_dispatch`.
- 2026-10-05: Reliable trigger in place. A cron-job.org job (owner's account, Europe/London, every 5 min) POSTs `workflow_dispatch` for `observe.yml`, using a fine-grained PAT scoped to this repo with Actions read/write. The PAT is stored only in cron-job.org and expires 2027-09-30. The first dispatch at 10:00:43Z started a run immediately. Disable the cron-job.org job after 2026-10-12 (runs are no-ops after that anyway).
- 2026-10-06 (interim, first full day on the reliable trigger):
  - **Release time confirmed: midnight London.** In the burst, 2026-11-09 was refused on all courts in the round starting 23:59:32 and open on all courts (08:00–15:00) in the round starting 23:59:54, whose probes ran until about 00:00:15.
  - **No race last night.** Every 11-09 slot was still free at 00:15. The first booking came at 06:45 (court 1, 08:00). This changes the 10-05 reading: the 11-08 slots "booked by 00:01" may have been pre-blocked (e.g. coaching), not raced. Several more midnights are needed to tell, and weekend target days may differ.
  - **Cancellations are common, contrary to the non-refundable prior.** There were 11 booked → free events on 10-05, including a Saturday 14:00–15:00 pair. One slot (court 1, 10-06 14:00) went free, booked and free again within hours. **Hypothesis:** some of these are unpaid checkout holds expiring, not true cancellations. Worth checking whether freed slots cluster right after a free → booked.
  - **Failures, by cause:**
    - (a) **GitHub runner starvation.** On 10-05 19:30–21:15, 5 runs got no runner for 15 min and were cancelled ("All jobs were cancelled" emails), leaving gaps of up to 35 min. This is GitHub-side, and one more reason not to host the product on GitHub Actions.
    - (b) **Camden/Cloudflare HTTP 520.** One transient scan error, at 16:45.
    - (c) **cron-job.org.** One dispatch failure, at 23:35 (likely a slow GitHub API).
    - (d) **Queue cancellations.** 18 "cancelled" runs were queue displacement (only one pending run is kept), which is expected.
  - **Change made:** runs now fail, and email, only after 3 consecutive errored runs; errors are still logged in the data files.
- 2026-10-07 (interim):
  - **Midnight release confirmed again.** 2026-11-10 opened on all courts between 23:59:55 and 00:00:15. No race: the first booking came at ~00:05 (court 1, 08:00) and the next at 08:20. The weekend check is still pending: Sat 11-14 opens at midnight on 10-09/10.
  - **Booked → free runs at 8–11 per day** (10-05: 11, 10-06: 10, 10-07: 8 by 16:00).
  - **Most frees look like expiring checkout holds.** Where the preceding free → booked was seen, the gap to booked → free clusters at ~45 min (17 of 25 in 44–47 min), with a smaller cluster at 5–10 min. This means a held slot often reappears ~45 min after it was taken, which is a design lever for [When to alert and how often to check](05-alert-triggers-and-poll-cadence.md).
  - **Reliability (10-06 07:30 to 10-07 16:00):** 380 success, 5 runner-starved cancellations, 4 transient 520s (absorbed by the 3-strikes rule), and 1 failure. That failure was a GitHub push 500 during a GitHub partial outage, made worse by a retry-loop bug (`rebase --abort` under `bash -e` ended the loop early). Fixed in `observe.yml`, and one run's data was lost.
- 2026-10-11 (interim):
  - **Weekend release is raced.** Sat 2026-11-14 opened at 23:59:55 on 10-10. Court 3 lost 09:00–12:00 within ~1 min. Court 1 lost 09:00 and 11:00–14:00 within ~2.5 min, with 11:00 and 12:00 blinking back and forth (checkout holds). Court 2's 10:00–12:00 were already blocked before release. All three 8am slots were still free at 00:15.
  - **Weekday releases (11-09 to 11-13) are not raced.** The first booking typically comes hours later; the exception is court 1 at 8am, sometimes taken at ~00:05–00:15. Some days have hours pre-blocked before release (e.g. 11-11 had only 4 of 8 hours open per court).
  - **Booked → free counts by day:** 11, 10, 9, 7, 3, 0, 2 (10-05 to 10-11). Of the 37 frees with a prior booking seen, 24 came 44–47 min after the booking, consistent with expiring checkout holds. Freed slots survive a median of ~6h before being re-booked (IQR 1.5h–28h); only 1 of 37 was re-taken within 10 min.
  - **Data artifact.** One scan at 10-09 20:20 returned a partial grid, so 112 slots "vanished" and reappeared at 20:25. A production scraper must treat missing slots as unknown, not as a change.
  - **Reliability (10-07 16:30 to 10-11 22:10):** 985 success, 13 runner-starved, 1 failure; 32 transient scan errors (29 × 520), 14 of them on 10-11.

## Answer

Closed on 2026-10-12, after the owner judged the data sufficient. The logger ran from 2026-10-04 to 2026-10-12 09:40, on GitHub Actions triggered by cron-job.org every 5 min, with a full 3-court scan each run.

- **Release time: midnight London, in one step.** The day at today+34 opens on all courts between 23:59:55 and 00:00:15. Seen on every night of the reliable-trigger period.
- **Weekend days are raced, weekdays are not.** Sat 2026-11-14 lost most of its morning slots within ~1–2.5 min of midnight. Weekday days usually see their first booking hours later; the exception is court 1 at 08:00, sometimes taken at ~00:05. Some hours are pre-blocked before release (likely coaching or bookings made by the venue), so they never appear as free.
- **Booked → free: 42 in the week,** falling over the week: 11, 10, 9, 7, 3, 0, 2, 0 per day (10-05 to 10-12). Most are expiring checkout holds, not real cancellations: of the 37 with the preceding booking seen, 24 freed 44–47 min after being taken. Freed slots then stay free for a median ~6 h (IQR 1.5–28 h); only 1 in 37 was re-taken within 10 min.
- **Scraper lessons for production:** treat slots missing from a scan as unknown, not as a change (one partial grid on 10-09 20:20 made 112 slots "vanish"). Expect transient Camden/Cloudflare 520s (about 1–3% of scans) and absorb them, e.g. with a 3-strikes rule. A full scan takes about 3 min (~1,110 slots).
- **Hosting lessons** (feed [Choose the hosting architecture](06-hosting-architecture.md)): GitHub's `schedule` trigger ran only about every 3 h. A `workflow_dispatch` from cron-job.org was reliable apart from ~1% of runs that couldn't get a GitHub runner. There were no Cloudflare challenges from GitHub runners.
- **Raw logs** (on `main`, written by `logger/observe.py`): `data/events.jsonl` (every slot change), `data/scans.jsonl` (per-scan summary), `data/probes.jsonl` (booking-window probes), `data/release_bursts.jsonl` (20-second polling around midnight), `data/state.json` (the last snapshot).
- **Teardown (done 2026-10-12):** `observe.yml` disabled on GitHub, cron-job.org job deleted, and its fine-grained PAT revoked.
