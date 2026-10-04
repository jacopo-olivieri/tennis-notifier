# Observe a week of releases and cancellations

Type: task
Mode: AFK
Status: open
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

At what time of day does a new day become bookable, and how often do booked slots become free again?

Run a temporary logger for about 7 days. It should take a snapshot of all 3 courts every 30–60 minutes, and also probe the `book.aspx` redirect for the first date past the window at several times: around 00:00, 06:00, 07:00 and 08:00. Record every booked → free change and every new date that appears. The logger may run on the owner's Mac temporarily, since it's an experiment and not the product. Running it on a cloud host instead would also test reachability.

The answer should record: the release time (or that it's continuous), the number of cancellations per week with their timing, and where the raw log lives.

See [Camden Active booking platform](../../../docs/research/camden_active_platform.md) for the scraping mechanics.
