# Observe a week of releases and cancellations

Type: task
Mode: AFK
Status: claimed
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
