# Map: Lincoln's Inn Fields court notifier

Label: wayfinder:map

## Destination

A build-ready spec for a free, always-on notifier. It tells a small invite-only group of members, via their chosen channel, when a Lincoln's Inn Fields slot matching one of their watches becomes bookable. Members manage their watches on a minimal website. It never books anything. The spec should be complete enough to implement v1 in one session.

## Notes

- Domain language: see `GLOSSARY.md` (Slot, Watch, Member, Release drop, Cancellation, Alert, Channel). Keep it current via the domain-modeling skill.
- Platform facts: [Camden Active booking platform](../../docs/research/camden_active_platform.md). Public HTML, no API, 3 courts, ~7s per request, bookable up to today + 34 days, non-refundable bookings.
- Settled in the charting session (2026-10-04):
  - **Members:** 5–20 friends, invite-only, sign in by email magic link.
  - **Watches:** recurring weekday + time window, or one-off date + window. Any court, 1-hour slots.
  - **Events:** both release drops and cancellations matter.
  - **Alerts:** notify only, never book. Re-alert every time a slot goes booked → free, at any hour, with no quiet hours.
  - **Channels:** members choose Telegram or email; WhatsApp only if it's cheap and easy.
  - **Website:** a simple, minimal one for managing watches.
  - **Hosting:** must be free and must not run on the owner's Mac.
- Poll politely: it's a council site.
- Ticket types: grilling tickets call the grilling and domain-modeling skills; research tickets call the research skill.

## Decisions so far

## Not yet specified

- **How often to check.** Depends on when new days release, how often cancellations happen, the ~7s request time and the host's cron limits. A burst around release time might be enough, with slow polling the rest of the day.
- **How slot state is stored and compared.** Detecting booked → free changes needs the previous snapshot. Where it lives depends on the host.
- **What an alert says.** Probably a deep link to book.aspx for the slot, plus the court and time. Maybe grouped when one release produces many matches.
- **Knowing when the scraper breaks.** The HTML or the postback flow can change silently, so the owner needs a "scraper unhealthy" signal.
- **Magic-link email delivery.** A free transactional email provider, possibly shared with the email channel.

## Out of scope

- Auto-booking: the tool notifies only. Booking would mean storing members' credentials and could break the site's terms.
- Public service open to anyone: membership stays invite-only.
- Venues other than Lincoln's Inn Fields (e.g. Kilburn Grange, Waterlow Park on the same system): may come later as a config change, but not in this effort.
- Quiet hours or muting: alerts go out immediately, and phones handle Do Not Disturb.
