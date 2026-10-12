# Choose the hosting architecture

Type: grilling
Mode: HITL
Status: resolved
Blocked by: 02, 04, 05
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Which free host, or combination of hosts, runs the poller, website and storage? How do they fit together (what runs where, where the state lives, how the website and the poller share data)? Does the choice support the checking schedule decided in [When to alert and how often to check](05-alert-triggers-and-poll-cadence.md)?

## Comments

- 2026-10-12: [Test whether cloud hosts can reach Camden Active](04-cloud-reachability-test.md) closed with GitHub runners proven and Supabase Edge Functions untested. If this grilling leans towards a non-GitHub poller, open a reachability task ticket for that host before committing to it. Key trade-off: GitHub Actions keeps the working Python scraper but depends on cron-job.org plus a PAT, and ~1% of runs get no runner (a risk at the midnight weekend race). Supabase pg_cron removes those, at the cost of a Deno rewrite and 150 s / 2 s CPU limits per invocation.

## Answer

Decided with the owner on 2026-10-12. All free tier; nothing runs on the owner's Mac.

**What runs where**
- **Poller:** the Python scraper on GitHub Actions in this public repo. The repo must stay public, because ~230 scans a day would exceed a private repo's free minutes. cron-job.org triggers each run through `workflow_dispatch`, using a fine-grained PAT that can only dispatch. GitHub's `schedule` trigger isn't used. It runs every 5 min from 07:00 to 23:00 and every 15 min overnight, with runs serialised by a concurrency group. No Supabase or Cloudflare reachability test is needed.
- **State:** Supabase Postgres, one free project. It holds members, watches, the slot snapshot, the alert log (pruned after 30 days) and the release and heads-up markers. No member data goes in the repo, because the repo is public. Sizing: snapshot ~31 KB, ~280 MB a month of egress against a 5 GB limit, and a DB well under 500 MB. The poller's queries every 5 min keep the project from being paused.
- **Website:** a static site on GitHub Pages from this repo (its domain is registered with BotFather `/setdomain`). It has one Supabase Edge Function as its whole API. The function verifies the Telegram Login Widget payload against the bot token and issues its own signed session token. It also handles watch create, read, update and delete with the service role. RLS denies all anonymous access, so the browser never talks to Postgres.
- **Telegram:** outbound only, with no webhook and no `getUpdates`. The widget is used with `request_access=write`, so signing in both connects the member and grants the bot permission to DM them. This replaces the `t.me/<bot>?start=<token>` linking step in [Choose the alert channels](07-choose-alert-channels.md).
- **Secrets:** the bot token is in GitHub secrets and in the Edge Function. The Supabase service key is in GitHub secrets. The dispatch PAT is in cron-job.org.

**How the checking schedule is met** (from [When to alert and how often to check](05-alert-triggers-and-poll-cadence.md))
- **Midnight burst:** cron-job.org dispatches a `release` job twice, at 23:45 and 23:50, which covers the ~1% of runs that get no runner. The first job to start claims tonight's release in Supabase, sleeps until 23:59:30, then bursts. The spare sees the claim and exits. Regular scans skip while the claim is held, so the site never has two pollers at once.
- **Heads-up:** no separate cron. The first scan at or after 20:00 London time sends the heads-ups unless Supabase records them as sent for today. This is safe across BST and GMT and when a run is missed.
- **New-watch alert:** sent by the Edge Function at the moment the watch is saved, using the latest snapshot (up to 5 or 15 min old, which is accepted).

**Shared logic in Postgres.** The poller (Python) and the Edge Function (TypeScript) can't share code, so the logic lives in the database. One SQL function matches a watch against the snapshot, excluding slots alerted in the last 30 min. Another formats the message and writes the alert log. Both callers only POST the returned text to Telegram.

**Retiring the logger:** the `observe` workflow and its `data/` commits stop once the notifier is live.
