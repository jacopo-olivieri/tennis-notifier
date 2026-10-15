# 10: Weekly grid UI

**What to build:** the decided website design for weekly watches: a Mon–Sun × hour grid with 5-week availability dots, per-date detail, the "Your watches" panel, the unsaved-changes bar, the footer and the unreachable banner, working on a phone. Spec: User Stories 16–19, 26–34 and 49–50; reference prototype `prototype/watch-website` (v2).

**Blocked by:** 04, 09

**Status:** ready-for-agent

- [x] The Weekly tab: clicking a cell watches that weekday and hour; each cell shows 5 dots (green = a court free that week, grey = booked); dashed cells for hours with no session
- [x] Selecting a cell shows the next five dates for that weekday and hour with which courts are free on each
- [x] The "Your watches" panel: Weekly and Single dates lists, contiguous hours merged into lines (e.g. "Sat · Sun 08:00–10:00"), each line's current free count and a × to remove it
- [x] Changes collect in an "N unsaved changes · Discard · Save" bar; Save sends one batch
- [x] Footer: last check time, bookable-until date, "Booking stays on Camden Active"
- [x] The banner "the bot can't message you — unblock it" shows while `unreachable_since` is set
- [ ] Mobile: the same layout stacked, with the detail directly under the grid; checked by hand against the prototype

## Comments

**2026-10-15:** Implemented; the hand check on a real phone is still to do (see the end of this comment).

- **`site/watches.js`** works out what the grid and panel show from `GET /state`. It's a pure ES module tested with `deno test site/`, which is now in CI. The spec's Testing Decisions now list it as a seam; rendering and clicks are still checked by hand.
  - A cell's five weeks are the next five dates of that weekday whose hour hasn't started, in London time, so the view's own rule. A date with no `availability` row is "not open" after `window_end`, otherwise "no session". The dots are green for free, grey for booked and hollow for no session or not open yet.
  - A cell is dashed when none of its five weeks has a court running. The grid's rows are the hours `availability` reports, as the spec's seasonal-hours note says, plus any watched weekly hour so it can be clicked off. Before the first scan the rows are 07:00–21:00.
  - Panel lines merge contiguous hours per day; weekdays with the same run share a line. Each line counts the courts free on its hours inside the window and carries its keys, so × removes the whole line.
  - The draft is the set of watch keys. Save sends `added = draft − saved` and `removed = saved − draft`, so clicking an hour on and off again isn't a change.
- **`site/app.js`** is now a module. The layout follows the prototype: the grid card, with the detail and "Your watches" beside it on desktop. On a phone everything stacks and the detail sits under the grid. Mouse press-and-drag paints cells and hover shows the detail; touch and keyboard toggle on click. The save bar shows the count, Discard and Save; save errors appear in it. After a save, a toast gives the outcome ("Saved." when only removing). The banner shows while `unreachable_since` is set. The footer shows the last check time, bookable-until date and "Booking stays on Camden Active".
- **No tab bar yet:** the only tab would be Weekly, so ticket 11 adds the bar with Single dates. Until then, single-date watches show in the panel and can be removed, but not added.
- **Local smoke run** (headless Brave against a fake API, 1200 px and 375 px): hover detail, drag-paint, click-off, discard, × then save (sent `removed` only), a phone tap showing the detail under the grid, Enter and Space on a focused cell, no horizontal scroll at 375 px, and the banner and footer text.
- **From the review:**
  - Fixed: × no longer works while a save is in flight; a mouse toggle can't swallow a later touch or keyboard click; a drag released outside the window stops painting; an old toast timer can't clear a newer toast; focus stays on a cell toggled from the keyboard; `app.js` reuses `watches.js`'s availability index.
  - Left as judgement calls: the status-to-label mapping lives in both the dot and the chip renderers. The banner clears on the next reload or save, not live, since nothing polls.
- **Still to do (HITL):** push main so Pages publishes `site/`, then check the layout on a phone against the prototype (`prototype/watch-website`, v2).
