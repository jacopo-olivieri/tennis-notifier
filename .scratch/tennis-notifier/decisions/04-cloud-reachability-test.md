# Test whether cloud hosts can reach Camden Active

Type: task
Mode: AFK
Status: resolved
Blocked by: 02
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Does Camden Active's Cloudflare front end let a full scan through (GET plus next-week postbacks, all 3 courts) when it runs from the top 1–2 hosting candidates in [Free hosting options for poller, website and storage](02-free-hosting-options.md)? Or does it block the requests or show a challenge?

Run a throwaway scan from each candidate a few times. The answer should record the status codes, any challenge pages, the timings, and which hosts are viable.

## Comments

- 2026-10-04: GitHub Actions (ubuntu-latest, Azure IPs) works. Run https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/37218179942 did a full scan (3 courts × 6 weeks, chained postbacks) plus 60 book.aspx checks with no challenge or block: 1158 slots, ~4 min. The observation logger keeps exercising this every 15 min until 2026-10-12, so it will also show whether blocking appears over time. Still untested: Supabase Edge Functions and Cloudflare Workers.

- 2026-10-12: Narrowed after [Free hosting options for poller, website and storage](02-free-hosting-options.md) was resolved. The two candidates are GitHub Actions and Supabase Edge Functions. GitHub-hosted runners are already proven by [Observe a week of releases and cancellations](01-observe-releases-and-cancellations.md): thousands of scans with no challenge, only transient 520s. Only Supabase Edge Functions still need a throwaway scan, and only if [Choose the hosting architecture](06-hosting-architecture.md) still wants them. If Supabase isn't on the table, this ticket can close with the logger data as its answer.

## Answer

Closed on 2026-10-12 using the logger data. The owner chose not to run a throwaway Supabase scan before the hosting decision is made.

- **GitHub-hosted runners (ubuntu-latest, Azure IPs): viable.** [Observe a week of releases and cancellations](01-observe-releases-and-cancellations.md) ran ~1,400 full scans (3 courts, chained postbacks, ~1,110 slots, ~3 min each) between 2026-10-04 and 2026-10-12. Cloudflare showed no challenge page and blocked nothing. The only errors were transient Camden/Cloudflare 520s in about 1–3% of scans, absorbed by a 3-strikes rule. Separately, ~1% of runs got no GitHub runner; that's a scheduling problem, not reachability.
- **Supabase Edge Functions: untested.** Testing them would mean a TypeScript/Deno rewrite and a free Supabase project. That only pays off if a Supabase-hosted poller is still in the running. Trade-offs as discussed: pg_cron removes cron-job.org, the PAT and GitHub runner starvation, but the 150 s wall and 2 s CPU limits force a per-court split and make the midnight burst tight.
- **Follow-up:** if [Choose the hosting architecture](06-hosting-architecture.md) leans towards a Supabase (or Cloudflare Workers) poller, it opens a short task ticket to run a throwaway scan from that host first.
