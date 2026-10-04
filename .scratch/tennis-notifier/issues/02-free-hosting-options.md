# Free hosting options for poller, website and storage

Type: research
Mode: AFK
Status: open
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Which free hosting setups can run all three of these: (a) a scheduled poller (a scan takes minutes because each request takes ~7s and needs a cookie jar and chained POST postbacks), (b) a minimal website with email magic-link sign-in, and (c) small persistent storage for members, watches and the last slot snapshot?

Compare candidates such as GitHub Actions cron with a static site plus a free DB, Cloudflare Workers (Cron Triggers, D1/KV, Pages), Vercel or Netlify with a cron and Supabase, Deno Deploy, Fly.io, and the Oracle Cloud free-tier VM. For each, record: the minimum cron interval and how reliable it is (e.g. GitHub Actions delays), the wall-time limit per run, outbound-request limits, storage, auth support, whether it's free-forever or a trial, and any known trouble reaching Cloudflare-fronted sites from that host's IPs.

## Comments

Research findings: docs/research/free_hosting_options.md on branch research/free-hosting-options
