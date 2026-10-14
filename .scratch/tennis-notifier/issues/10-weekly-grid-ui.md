# 10: Weekly grid UI

**What to build:** the decided website design for weekly watches: a Mon–Sun × hour grid with 5-week availability dots, per-date detail, the "Your watches" panel, the unsaved-changes bar, the footer and the unreachable banner, working on a phone. Spec: User Stories 16–19, 26–34 and 49–50; reference prototype `prototype/watch-website` (v2).

**Blocked by:** 04, 09

**Status:** ready-for-agent

- [ ] The Weekly tab: clicking a cell watches that weekday and hour; each cell shows 5 dots (green = a court free that week, grey = booked); dashed cells for hours with no session
- [ ] Selecting a cell shows the next five dates for that weekday and hour with which courts are free on each
- [ ] The "Your watches" panel: Weekly and Single dates lists, contiguous hours merged into lines (e.g. "Sat · Sun 08:00–10:00"), each line's current free count and a × to remove it
- [ ] Changes collect in an "N unsaved changes · Discard · Save" bar; Save sends one batch
- [ ] Footer: last check time, bookable-until date, "Booking stays on Camden Active"
- [ ] The banner "the bot can't message you — unblock it" shows while `unreachable_since` is set
- [ ] Mobile: the same layout stacked, with the detail directly under the grid; checked by hand against the prototype
