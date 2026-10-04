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
