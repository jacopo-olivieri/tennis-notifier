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
