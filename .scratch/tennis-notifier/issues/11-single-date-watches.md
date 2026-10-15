# 11: Single-date watches

**What to build:** the Single dates tab: a 7-week calendar with each day's free count; clicking a day shows the hours a court runs and lets the Member watch any of them, including dates not yet bookable. Spec: User Stories 20–25; reference prototype `prototype/watch-website` (v2).

**Blocked by:** 10

**Status:** resolved

- [x] A 7-week calendar showing each day's free count; copy "Click a day, then the hours you want to play."
- [x] Clicking a day lists only the hours when a court runs, each marked "✓ Weekly" (covered by a weekly watch, not clickable), "✓ Watching", "N free" or "Booked"
- [x] Days after `window_end()` show as "not open" with the date booking opens, and can be watched
- [x] Single-date watches appear in the panel's Single dates list and save through the same batch
- [x] A past single-date watch no longer shows (housekeeping deletes it in 13; until then the site hides it)

## Comments

**2026-10-15:** Implemented; still to do: push main so Pages publishes it, then a look on a phone.

- **`site/watches.js`** gains four pure functions, tested with `deno test site/`:
  - `calendar` gives the seven weeks from this Monday. Each day carries its free count, which is free court-hours on its hours still to come, as in the prototype. It also says whether the day is past, not open (after `window_end`) or has a watched hour.
  - `dayHours` gives a day's hours: those a court runs, plus that date's own watched hours. Each is "weekly", "watching", "free", "booked" or "not open". A day past `window_end` that wasn't scanned takes its weekday's latest scanned hours. A bookable day with nothing left shows no hours rather than last week's.
  - `opensOn` puts the booking-open date as far before the date as `window_end` is after today, so the 34 lives only in SQL.
  - `upcoming` drops single-date hours that have started.
- **`site/app.js`** adds the Weekly / Single dates tab bar (with line counts), the calendar card, and the day card ("✓ Weekly" is a plain box, not a button). A not-open day says "Booking opens at midnight on …". `showMember` filters the saved watches through `upcoming`, so a past single-date watch is hidden and isn't sent as `removed`. Single-date hours go into the same draft and batch as weekly ones.
- **Local smoke run** (headless Brave against a fake API, 1200 px and 375 px):
  - 49 days, with the three past ones disabled; "✓ Weekly" on a Saturday at 08:00.
  - Toggling a free hour gives "1 unsaved change". A day six weeks out shows its hours as "Not open" with "Booking opens at midnight on Sun 25 Oct".
  - Save posted only the three new dated hours, with `removed` empty even though yesterday's watch was hidden.
  - No horizontal scroll at 375 px. On a phone the day card sits under the calendar; it was missing a gap above "Your watches", now fixed.
- **From the review:**
  - Fixed: the header comment, a helper shadowing `runs`, `opensOn`'s raw millisecond maths, and a misnamed test.
  - Left:
    - A page left open past midnight works out past days and the booking-open date from the browser's clock but `window_end` from the last load. It's off by a day until the next reload or save, the same as the banner in ticket 10.
    - A single-date hour later also covered by a weekly watch keeps both. The day shows "✓ Weekly" and the dated one can only be removed with × in the panel, as in the prototype.
    - `toggleDated` sits beside `toggle` rather than merging with it, since only weekly toggles move the grid's focus.

**2026-10-15:** Live. Main was pushed as 00c53eb; `test` and `pages` passed. The owner checked the Single dates tab on a phone, and it looks right.
