# Draft the alert and heads-up messages

Type: prototype
Mode: HITL
Status: resolved
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

What do the Telegram messages say? Cover the grouped alert (slots grouped by date and time, each with a booking link), the new-watch alert, and the 20:00 heads-up (which says slots *should* open). Which deep link goes with each slot: does a `book.aspx` URL land the member on the right slot, or only on the court and week? Draft sample messages from real data in `data/` to react to.

## Comments

- 2026-10-12: From [Prototype the watch-management website](08-watch-management-website.md): the new-watch alert goes out once per save and lists only slots matched by the hours added in that save. Single-date watches can be for days not yet open, so the heads-up also covers them. The site's wording uses "Weekly" and "Single dates", "N free" and "Booked".

- 2026-10-12: From [Design the Supabase data model and shared matching functions](09-data-model-and-shared-functions.md): messages are formatted in SQL by one shared step, so the wording must be producible from rows `(member, kind, court, date, hour)` grouped per member. The heads-up lists watched hours on the next release day where at least one court shows free. A single message can mix cancellations with retried unsent alerts. The new-watch message lists only the hours added in that save.

## Answer

Resolved 2026-10-12 with the owner, using the throwaway prototype `PROTOTYPE-alert-wording.html` on branch `prototype/alert-wording`. The owner picked variant A, the short list.

**Links.** A `book.aspx?fdCourseEventId=…&fdDate=…&fdTime=…` link never opens the slot. Signed out, it redirects with a 302 to the court's detail page for the current week, whether the slot is free, booked or outside the booking window. The owner tested it signed in on their phone, and it also opens the court page. So each court gets one link: its detail page (`/courses/detail/171|176|177/…`). Messages carry no links to individual slots, and members find the date on the court's grid themselves.

**Format.** Telegram `sendMessage` with `parse_mode: HTML`, with no inline keyboard and no footer link. A bold headline comes first, then a blank line, then one line per date and hour in date-then-hour order:

```
<date> <HH:00>  C1 C2 C3
```

- `<date>` is `Sun 22 Nov` (weekday, day of month, short month, with no year), and the time is in 24-hour London time.
- Courts are listed in ascending order as `C<n>`. In alerts, each `C<n>` is `<a href="{court detail page}">C<n></a>`.
- Two spaces separate the time from the courts.

**Headlines.**

| Message | Headline | Extra |
|---|---|---|
| Release-drop alert | `🎾 Just released` | |
| Cancellation alert | `🎾 Court free` (one slot) / `🎾 Courts free` (more) | |
| Mixed alert (a check combining kinds, e.g. a cancellation plus a retried unsent release alert) | `🎾 Free now` | |
| New-watch alert | `🎾 Free now for your new watches` | A second line lists the hours added in that save, joined by ` · `: weekly hours as `Weekly Tue 11:00`, single dates as `Fri 23 Oct 15:00` |
| Heads-up (20:00) | `🌙 Opens at midnight` | Lines list the courts free on the grid now, **with no links** (nothing is bookable yet) |

Samples:

```
🎾 Just released

Sun 22 Nov 09:00  C1 C2 C3
Sun 22 Nov 10:00  C1 C2 C3

🎾 Court free

Wed 14 Oct 10:00  C3

🎾 Free now for your new watches
Weekly Tue 11:00 · Fri 23 Oct 15:00

Tue 20 Oct 11:00  C1
Tue 27 Oct 11:00  C2 C3

🌙 Opens at midnight

Sun 22 Nov 09:00  C1 C2 C3
Sun 22 Nov 10:00  C3
```

All of this can be produced from rows `(member, kind, court, date, hour)`, plus the hours added in that save for the new-watch alert, so the shared SQL formatting step from [Design the Supabase data model and shared matching functions](09-data-model-and-shared-functions.md) holds as designed.
