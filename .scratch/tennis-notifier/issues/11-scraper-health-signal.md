# Decide how the owner learns the notifier is broken

Type: grilling
Mode: HITL
Status: open
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

How does the owner find out when the notifier stops working, without false alarms from the transient 520s? Silent failure modes:
- Camden's HTML or postback flow changes, so a scan parses zero slots or garbage.
- cron-job.org stops dispatching, or the PAT expires.
- GitHub runs fail or get no runner.
- Supabase is unreachable.
- The Telegram bot token is revoked.

What counts as unhealthy, who is told, and through what (an owner Telegram DM, an external heartbeat monitor)?

Context: [Choose the hosting architecture](06-hosting-architecture.md).

## Comments


- 2026-10-12: From [Design the Supabase data model and shared matching functions](09-data-model-and-shared-functions.md), the available signals are: `scan_log` (one row per court per attempt: ok, slot count, error); a court counts as a parse failure if it doesn't parse all 6 weeks or returns <50% of its previous slots; a `release` marker whose lease lapsed at 00:15 without `done_at`; alerts with `failures >= 3` (e.g. a 403 from a member blocking the bot); and `last_seen_at` on slots.
