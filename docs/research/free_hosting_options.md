# Free hosting options for poller, website and storage

Research for ticket 02 (`.scratch/tennis-notifier/issues/02-free-hosting-options.md`). Sources are official docs and pricing pages, read on 2026-10-04. Anything I couldn't confirm from a primary source is marked **(unverified)**.

## What the workload needs

From [camden_active_platform.md](camden_active_platform.md):

- **Poller.** One full scan is 3 courts × about 5–6 weeks, so about 15–18 sequential requests at about 7s each. That's about 2–2.5 minutes of wall time, but almost no CPU. It needs a cookie jar and chained ASP.NET postbacks, and the target sits behind Cloudflare.
- **Website.** A minimal page for managing watches, with email magic-link sign-in for 5–20 members.
- **Storage.** A few KB to MB: members, watches and the last slot snapshot.

## Comparison

| Option | Min cron interval / reliability | Wall time per run | CPU / outbound limits | Storage | Auth | Free forever? | Cloudflare-fronted target |
|---|---|---|---|---|---|---|---|
| **GitHub Actions cron** (poller only) | 5 min. "Can be delayed during periods of high loads… High load times include the start of every hour… some queued jobs may be dropped." In public repos, schedules are disabled after 60 days without repo activity. [1] | 6 h per job [2] | No CPU cap. Outbound HTTP isn't limited (the documented limits are GitHub's own API). [2] | None built in; use an external DB, or commit JSON to the repo | None | Yes. Standard runners are free in public repos. Private repos get 2,000 min/month on Free [3], which isn't enough for polling every 15 min at about 3 min a run. | Runners are Azure VMs [4], so traffic comes from datacenter IPs. Untested against Camden. |
| **Cloudflare Workers** (Cron Triggers + D1/KV + Pages) | Every minute (`* * * * *` is a documented example). 5 cron triggers per account. Edits take up to 15 min to propagate. [5][6] | Cron: 15 min wall clock [6] | **Cron gets 10 ms CPU on Free.** 50 subrequests per invocation, 6 simultaneous connections, 128 MB memory. [6] Queues are on Free with 10k ops/day [7], so work can be split across invocations. | D1: 500 MB per DB, 5 GB per account, 5M rows read and 100k rows written per day [8][9] | None built in; magic links must be hand-rolled, plus an email provider | Yes (Workers Free) | Requests come from Cloudflare itself and carry a `CF-Worker` header. Zones can filter them with WAF rule `cf.worker.upstream_zone` [10]. Untested against Camden. |
| **Vercel Hobby** + Supabase | **Once per day**, ±59 min. More frequent expressions fail at deploy. [11] | 300 s max (Hobby) [12] | Billed on active CPU (I/O wait isn't counted) [12] | Use Supabase | Use Supabase | Yes | Functions run in AWS `iad1` by default [12]. Untested. |
| **Netlify Free** + Supabase | Cron supported; docs don't state a minimum interval [13] | **30 s** for scheduled functions [13] | 300 credits/month hard limit; functions cost 10 credits per GB-hour [14] | Netlify DB/Blobs, or Supabase | Use Supabase | "$0 forever" with a hard credit cap [14][15] | Untested |
| **Supabase** alone (Cron → Edge Function + Postgres + Auth) | pg_cron runs "from every second to once a year" and can call Edge Functions via HTTP [16] | Edge Function: **150 s wall** on Free, 2 s CPU [17] | 256 MB memory. Ports 25/587 are blocked [17]. 500k invocations/month [18]. | 500 MB Postgres per project, 2 active projects [18] | Built-in magic link, 50k MAU. The built-in SMTP sends only **2 emails/hour**, so custom SMTP is needed. [18][19] | Yes, but **paused after 1 week of inactivity**. A daily poller doing DB queries should keep it active. [18][20] | Edge runtime egress IPs are unknown **(unverified)**. Untested. |
| **Deno Deploy** (new platform) | `Deno.cron` is supported, max 10 crons per revision on Free. Docs give no minimum interval. No overlapping runs, up to 5 retries. [21] | **Not documented (unverified)** | Free tier: 1M requests/month, 10 h active CPU/month, 20 GiB egress [22] | Deno KV 1 GiB [22] | None built in | Yes | Untested |
| **Fly.io** | Any interval (always-on machine) | Unlimited | Normal VM | Volumes (billed) | None | **No.** "New organizations don't have a free tier." The trial is 2 h of machine time or 7 days. Cheapest always-on machine is $2.19 per 30 days. [23] | Untested |
| **Oracle Cloud Always Free VM** | Any interval (cron/systemd on a VM) | Unlimited | AMD micro: 1/8 OCPU, 1 GB RAM, 50 Mbps. A1 Arm: 2 OCPU/12 GB total. 10 TB/month egress. [24] | 200 GB block storage, plus 2× Autonomous DB at 20 GB each [24] | None; self-host | Yes ("Always Free"), but **idle instances may be reclaimed**: p95 CPU, network (and memory on A1) all under 20% over 7 days [24]. A light poller would meet that "idle" test. Sign-up needs a card, and A1 capacity is often unavailable **(both unverified)**. | Oracle datacenter IPs. Untested. |

Static hosting for the website, if the poller lives elsewhere, can be GitHub Pages or Cloudflare Pages (free; not compared further here).

## Takeaways

- **Fly.io is out** (no free tier). **Vercel Hobby is out** (daily cron only). **Netlify is a poor fit**: 30 s scheduled-function limit and a hard credit cap.
- **Cloudflare Workers** has the best cron (every minute, 15 min wall). But a 10 ms CPU budget per cron invocation is very tight for parsing about 18 HTML pages with large `__VIEWSTATE`s. It would probably need one invocation per court-week chained through Queues **(unverified whether parsing fits in 10 ms)**. Its egress also goes Cloudflare-to-Cloudflare, which Camden's zone can single out by WAF rule.
- **Oracle** has no runtime limits, but the idle-reclamation rule and the ops burden of a whole VM make it a fallback, not a first choice.
- **None of the sources say whether Camden's Cloudflare zone challenges any of these hosts' IPs.** That is the biggest open risk, and ticket 04 has to test it empirically.
- **Every option needs a custom SMTP or transactional email provider** for magic links. Supabase's built-in sender (2/hour) isn't enough.

## Recommendation for ticket 04

1. **GitHub Actions cron (public repo) + Supabase (Postgres + Auth) + static site on GitHub Pages or Cloudflare Pages.** Actions has no runtime or CPU cap, so the Python/urllib scraper works as-is. Polling every 5–15 min is enough for this use case. Its weaknesses are cron jitter and dropped runs at the top of the hour (schedule at odd minutes like `7,22,37,52`) and the 60-day disable rule for public repos. A scheduled commit or the owner's activity avoids that rule **(confirm what counts as "activity")**.
2. **Supabase-only: pg_cron → Edge Function per court + Postgres + Auth.** Everything lives in one place and cron intervals can be sub-minute. One court's scan (about 6 requests × 7 s ≈ 42 s) fits the 150 s wall limit, so schedule three jobs, one per court. It needs a rewrite in TypeScript/Deno.

Test both in ticket 04 from their real IPs: a GET plus a two-step postback chain against Court 1. They share the same Supabase DB and auth, so comparing them costs little. If both get Cloudflare challenges, try Cloudflare Workers (with Queues fan-out) next, then an Oracle VM.

## Sources

1. GitHub, Events that trigger workflows (`schedule`): https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
2. GitHub Actions limits: https://docs.github.com/en/actions/reference/limits
3. GitHub Actions billing: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
4. GitHub-hosted runners: https://docs.github.com/en/actions/concepts/runners/github-hosted-runners
5. Cloudflare Cron Triggers: https://developers.cloudflare.com/workers/configuration/cron-triggers/
6. Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
7. Cloudflare Queues pricing: https://developers.cloudflare.com/queues/platform/pricing/
8. Cloudflare D1 limits: https://developers.cloudflare.com/d1/platform/limits/
9. Cloudflare D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/
10. Cloudflare HTTP headers (`CF-Worker`): https://developers.cloudflare.com/fundamentals/reference/http-headers/
11. Vercel cron usage and pricing: https://vercel.com/docs/cron-jobs/usage-and-pricing
12. Vercel Functions limits: https://vercel.com/docs/functions/limitations
13. Netlify scheduled functions: https://docs.netlify.com/build/functions/scheduled-functions/
14. Netlify credit-based plans: https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/
15. Netlify pricing: https://www.netlify.com/pricing/
16. Supabase Cron: https://supabase.com/docs/guides/cron
17. Supabase Edge Function limits: https://supabase.com/docs/guides/functions/limits
18. Supabase pricing: https://supabase.com/pricing
19. Supabase Auth rate limits: https://supabase.com/docs/guides/auth/rate-limits
20. Supabase project pausing: https://supabase.com/docs/guides/platform/free-project-pausing
21. Deno Deploy cron: https://docs.deno.com/deploy/reference/cron/
22. Deno Deploy pricing: https://deno.com/deploy/pricing
23. Fly.io pricing: https://docs.fly.io/about/pricing
24. Oracle Cloud Always Free resources: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
