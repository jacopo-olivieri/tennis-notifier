# Test whether cloud hosts can reach Camden Active

Type: task
Mode: AFK
Status: open
Blocked by: 02
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Does Camden Active's Cloudflare front end let a full scan through (GET plus next-week postbacks, all 3 courts) when it runs from the top 1–2 hosting candidates in [Free hosting options for poller, website and storage](02-free-hosting-options.md)? Or does it block the requests or show a challenge?

Run a throwaway scan from each candidate a few times. The answer should record the status codes, any challenge pages, the timings, and which hosts are viable.

## Comments

- 2026-10-04: GitHub Actions (ubuntu-latest, Azure IPs) works. Run https://github.com/jacopo-olivieri/tennis-notifier/actions/runs/37218179942 did a full scan (3 courts × 6 weeks, chained postbacks) plus 60 book.aspx checks with no challenge or block: 1158 slots, ~4 min. The observation logger keeps exercising this every 15 min until 2026-10-12, so it will also show whether blocking appears over time. Still untested: Supabase Edge Functions and Cloudflare Workers.

- 2026-10-12: Narrowed after [Free hosting options for poller, website and storage](02-free-hosting-options.md) was resolved. The two candidates are GitHub Actions and Supabase Edge Functions. GitHub-hosted runners are already proven by [Observe a week of releases and cancellations](01-observe-releases-and-cancellations.md): thousands of scans with no challenge, only transient 520s. Only Supabase Edge Functions still need a throwaway scan, and only if [Choose the hosting architecture](06-hosting-architecture.md) still wants them. If Supabase isn't on the table, this ticket can close with the logger data as its answer.
