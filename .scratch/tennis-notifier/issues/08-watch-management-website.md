# Prototype the watch-management website

Type: prototype
Mode: HITL
Status: resolved
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

What does the minimal website look like and how does it behave? Cover signing in, adding and removing recurring and one-off watches, choosing a channel, and (for the owner) inviting members. Build a rough clickable mock to react to. No backend.

## Comments

- 2026-10-12: From [Choose the hosting architecture](06-hosting-architecture.md), the site is static on GitHub Pages and talks to one Edge Function API. Signing in with the Telegram widget (`request_access=write`) is also how the channel gets connected, so there's no separate "choose a channel" or `/start` step. Saving a watch triggers the new-watch alert at once.

## Answer

Resolved 2026-10-12. The site is a **week grid** (variant B), picked over a list + form (A) and sentence cards with a guided builder (C).

Prototype: branch `prototype/watch-website`, file `site/prototype/watches_prototype.html` (v2, the decided design; `watches_prototype_v1.html` has all three variants). Open the file directly; the black bar picks the screen.

**Watches are chosen hours, not time windows.**
- **Weekly** tab: a Mon–Sun × hour grid. Clicking a cell watches that weekday and start hour every week. Copy: "Click the hours you want to play (weekly)."
- Each cell shows one dot for each of the next 5 weeks (green = a court free that week, grey = booked; dashed cell = no court that hour this season). Selecting a cell shows the next five dates for that weekday and hour, and which courts are free on each.
- **Single dates** tab: a 7-week calendar with each day's free count. Clicking a day shows only the hours when a court runs; clicking an hour watches it for that date. Copy: "Click a day, then the hours you want to play." Hours already covered by Weekly show "✓ Weekly" and can't be clicked; watched hours show "✓ Watching"; the rest say "N free" or "Booked".
- Dates not bookable yet (past today + 34) **can** be watched; they show as "not open" with the date booking opens, and get the 20:00 heads-up then the midnight alert.
- A single-date watch is **deleted quietly** once its date has passed.
- **No pause switch** in v1: members click hours off and back on.
- **Your watches** panel: two short lists, Weekly and Single dates, contiguous hours merged into lines (e.g. "Sat · Sun 08:00–10:00"), each line with its current free count and a × to remove it.
- **Explicit save:** changes collect in an "N unsaved changes · Discard · Save" bar. One save sends **one** new-watch alert, listing slots now free for the hours added in that save only.

**Sign-in and members.**
- Signed out: one "Log in with Telegram" button (the widget with write access), saying that logging in lets the bot message you. No separate channel step.
- Not a member: "This one's invite-only… ask Jacopo for an invite link".
- **Owner** only: a Members tab with the member list (name, Telegram handle, hours watched, Remove), and **single-use invite links**: "Create invite link", copy, revoke; each expires after 7 days, and the first person to open it and log in becomes a member. The invite landing page says "Jacopo invited you".
- Account menu: name, handle, Log out. Footer: last check time, bookable-until date, "Booking stays on Camden Active".

Mobile: the same layout stacked; the per-week detail appears directly under the grid.
