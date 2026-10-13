# Decide how the owner learns the notifier is broken

Type: grilling
Mode: HITL
Status: resolved
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

## Answer

Decided with the owner on 2026-10-13.

**Outside alarm only.** The notifier never reports on itself. A Healthchecks.io dead-man's switch (free plan) alerts when the expected pings stop. This covers every silent failure, including cron-job.org stopping, an expired PAT, no runner, Supabase down and a revoked bot token. There's no inside path that sends the owner a DM.

**Who is told.** Only the owner, through Healthchecks.io's own Telegram integration (a separate bot from ours, so a revoked token can't silence it) with email as a backup. Members aren't told about outages. Healthchecks also sends a notice when the check recovers.

**Two checks:**

| Check | Pinged when | Schedule (Europe/London) | Grace |
|---|---|---|---|
| `scan` | `record_scan` succeeds, **all 3 courts** are complete, and no Telegram send in that run returns 401 (a member's 403 still counts as fine) | Matches cron-job.org: every 5 min 07:00–23:00, every 15 min overnight | 30 min |
| `release` | `record_release` sets `done_at` | Daily at 00:00 | 20 min |

Why these conditions:
- A transient 520 just skips one ping, and the grace period absorbs it.
- A Camden HTML or postback change makes every court fail to parse, so the pings stop.
- If Supabase is unreachable, `record_scan` fails, so the pings stop.
- A revoked token returns 401, so the pings stop.

The worst case is learning about a real outage about 35 minutes late. A missed midnight release doesn't show on `scan`, because regular scans resume at 00:15. That's why `release` is its own check.

**Members the bot can't reach** (403, e.g. they blocked the bot): this isn't a health problem, so the owner gets no alarm. The website shows that member a banner: "the bot can't message you — unblock it". This needs a per-member "unreachable since" fact, set when their alerts hit 3 failures with a 403 and cleared on the next successful send.

**Credentials.** Nothing special. The dispatch PAT gets the maximum expiry, and rotating it is a step in the deploy runbook. GitHub's expiry email and the `scan` check are the safety nets.

**Spec impact:** two Healthchecks ping URLs live in GitHub secrets; there's a `members.unreachable_since` column (or equivalent) and the site banner; and pings are sent after the Telegram sends, so a 401 can withhold them.
