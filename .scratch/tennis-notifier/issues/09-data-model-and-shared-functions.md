# Design the Supabase data model and shared matching functions

Type: grilling
Mode: HITL
Status: open
Blocked by: 08
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

What tables, columns and SQL functions does Supabase hold so that the poller and the Edge Function share one source of truth? Cover:
- members and invites
- watches, both recurring and one-off
- the slot snapshot and how a scan is compared with it to detect release drops and cancellations (booked → free)
- the alert log behind the 30-minute no-repeat rule
- the release-claim and heads-up markers
- the signatures of the shared "match a watch" and "format and record an alert" functions

Also: what happens when a scan is partial or fails midway, so that a half-scan doesn't produce a burst of false "free" changes?

Context: [Choose the hosting architecture](06-hosting-architecture.md).

## Comments

- 2026-10-12: From [Prototype the watch-management website](08-watch-management-website.md):
  - A watch is a set of chosen hours, not a window: weekly (weekday + start hour) and single-date (date + start hour) rows. "Sat · Sun 08:00–10:00" is only how the site displays them.
  - Single-date hours may be later than today + 34 (they need the heads-up). Past ones are deleted quietly.
  - Invites are single-use tokens with a 7-day expiry, plus revoke. There is one owner, who can remove members (their watches go with them).
  - A save is a batch of added and removed hours. The new-watch alert covers only the slots matched by hours added in that save.
  - The site needs, per weekday and hour, the next 5 weeks' status (free / booked / no session) and the free courts per date and hour, both read from the snapshot.
  - Data issue: the current snapshot has "free" slots after today + 34 (up to 22 Nov on 12 Oct). These are probably not bookable yet, so the scan or the snapshot must cut at the booking window, or a not-yet-open day will look like a cancellation or release.
