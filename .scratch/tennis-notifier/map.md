# Map: Lincoln's Inn Fields court notifier

Label: wayfinder:map

## Destination

A build-ready spec for a free, always-on notifier. It tells a small invite-only group of members, by Telegram, when a Lincoln's Inn Fields slot matching one of their watches becomes bookable. Members manage their watches on a minimal website. It never books anything. The spec should be complete enough to implement v1 in one session.

## Notes

- Domain language: see `GLOSSARY.md` (Slot, Watch, Member, Release drop, Cancellation, Alert, Channel). Keep it current via the domain-modeling skill.
- Platform facts: [Camden Active booking platform](../../docs/research/camden_active_platform.md). Public HTML, no API, 3 courts, ~7s per request, bookable up to today + 34 days, non-refundable bookings.
- Settled in the charting session (2026-10-04):
  - **Members:** 5–20 friends, invite-only. Sign-in is decided under [Choose the alert channels](issues/07-choose-alert-channels.md).
  - **Watches:** recurring weekday + time window, or one-off date + window. Any court, 1-hour slots.
  - **Events:** both release drops and cancellations matter.
  - **Alerts:** notify only, never book. Re-alert every time a slot goes booked → free, at any hour, with no quiet hours.
  - **Website:** a simple, minimal one for managing watches.
  - **Hosting:** must be free and must not run on the owner's Mac.
- Poll politely: it's a council site.
- Ticket types: grilling tickets call the grilling and domain-modeling skills; research tickets call the research skill.

## Decisions so far

- [Observe a week of releases and cancellations](issues/01-observe-releases-and-cancellations.md): Days open at midnight London. Weekend mornings are raced within minutes; weekdays aren't. About 1–11 booked → free per day, mostly checkout holds expiring ~45 min after booking. GitHub's own scheduler is unusable, but an external cron dispatch works.
- [Alert channel options: WhatsApp, Telegram, email](issues/03-alert-channel-options.md): WhatsApp costs per message, email needs a domain, Telegram is free and handles bursts.
- [Choose the alert channels](issues/07-choose-alert-channels.md): Telegram bot DMs only, with Telegram login for the website; no email or WhatsApp.
- [Free hosting options for poller, website and storage](issues/02-free-hosting-options.md): Fly, Vercel and Netlify are out. The front-runner is GitHub Actions (triggered by an external cron, since GitHub's own scheduler is throttled) plus Supabase and a static site; the alternative is Supabase alone; the fallbacks are Cloudflare Workers, then an Oracle VM.

## Not yet specified

- **How slot state is stored and compared.** Detecting booked → free changes needs the previous snapshot. Where it lives depends on the host.
- **What an alert says.** Probably a deep link to book.aspx for the slot, plus the court and time. Maybe grouped when one release produces many matches.
- **Knowing when the scraper breaks.** The HTML or the postback flow can change silently, so the owner needs a "scraper unhealthy" signal.

## Out of scope

- Auto-booking: the tool notifies only. Booking would mean storing members' credentials and could break the site's terms.
- Public service open to anyone: membership stays invite-only.
- Venues other than Lincoln's Inn Fields (e.g. Kilburn Grange, Waterlow Park on the same system): may come later as a config change, but not in this effort.
- Email and WhatsApp alerts: v1 is Telegram only (see [Choose the alert channels](issues/07-choose-alert-channels.md)).
- Quiet hours or muting: alerts go out immediately, and phones handle Do Not Disturb.
