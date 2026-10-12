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
