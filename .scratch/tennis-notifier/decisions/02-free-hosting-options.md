# Free hosting options for poller, website and storage

Type: research
Mode: AFK
Status: resolved
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Which free hosting setups can run all three of these: (a) a scheduled poller (a scan takes minutes because each request takes ~7s and needs a cookie jar and chained POST postbacks), (b) a minimal website with email magic-link sign-in, and (c) small persistent storage for members, watches and the last slot snapshot?

Compare candidates such as GitHub Actions cron with a static site plus a free DB, Cloudflare Workers (Cron Triggers, D1/KV, Pages), Vercel or Netlify with a cron and Supabase, Deno Deploy, Fly.io, and the Oracle Cloud free-tier VM. For each, record: the minimum cron interval and how reliable it is (e.g. GitHub Actions delays), the wall-time limit per run, outbound-request limits, storage, auth support, whether it's free-forever or a trial, and any known trouble reaching Cloudflare-fronted sites from that host's IPs.

## Answer

Full comparison: `docs/research/free_hosting_options.md` on branch `research/free-hosting-options` (sources read 2026-10-04).

- **Ruled out:** Fly.io (no free tier any more), Vercel Hobby (cron at most once a day), Netlify Free (30 s limit for scheduled functions, hard credit cap).
- **Candidate 1: GitHub Actions + Supabase (Postgres, plus Auth if useful) + a static site on GitHub Pages or Cloudflare Pages.** No CPU or runtime cap, so the existing Python scraper works as it is. Free only in a public repo.
- **Candidate 2: Supabase alone.** pg_cron calls one Edge Function per court (150 s wall limit, 2 s CPU on Free). Needs a TypeScript/Deno rewrite. The project is paused after a week of inactivity, but a working poller keeps it active.
- **Fallbacks:** Cloudflare Workers (cron every minute, but only 10 ms of CPU per invocation on Free, and Camden's zone can single out Worker traffic), then an Oracle Always Free VM (no limits, but idle instances can be reclaimed and the owner has a VM to run).

**Updated by what [Observe a week of releases and cancellations](01-observe-releases-and-cancellations.md) has seen so far (2026-10-12):**
- GitHub's `schedule` trigger is unusable for anything time-sensitive. It ran about every 3 h, not every 5 min. A cron-job.org job that POSTs `workflow_dispatch` every 5 min proved reliable, apart from occasional runs where no runner was available.
- GitHub-hosted runners can reach Camden through Cloudflare. Over thousands of runs there were no challenges, only transient 520s. This answers the reachability question for Candidate 1.
- Sign-in is now Telegram login, not email magic links (see [Choose the alert channels](07-choose-alert-channels.md)). The auth and SMTP columns of the research therefore matter less, and no transactional email provider is needed.
