# 11: Single-date watches

**What to build:** the Single dates tab: a 7-week calendar with each day's free count; clicking a day shows the hours a court runs and lets the Member watch any of them, including dates not yet bookable. Spec: User Stories 20–25; reference prototype `prototype/watch-website` (v2).

**Blocked by:** 10

**Status:** ready-for-agent

- [ ] A 7-week calendar showing each day's free count; copy "Click a day, then the hours you want to play."
- [ ] Clicking a day lists only the hours when a court runs, each marked "✓ Weekly" (covered by a weekly watch, not clickable), "✓ Watching", "N free" or "Booked"
- [ ] Days after `window_end()` show as "not open" with the date booking opens, and can be watched
- [ ] Single-date watches appear in the panel's Single dates list and save through the same batch
- [ ] A past single-date watch no longer shows (housekeeping deletes it in 13; until then the site hides it)
