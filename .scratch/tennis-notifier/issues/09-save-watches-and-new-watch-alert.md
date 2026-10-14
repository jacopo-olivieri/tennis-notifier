# 09: Save watches and the new-watch alert

**What to build:** a signed-in Member adds and removes watched hours (weekly or single-date) and saves them as one batch, and immediately gets one `🎾 Free now for your new watches` DM listing the slots already free for the hours added in that save. The UI here is a plain list; the week grid comes in 10. Spec: `save_watches`, `availability` view, `POST /watches`, Message format (new watch).

**Blocked by:** 03, 08

**Status:** ready-for-agent

- [ ] The `availability(date, hour, free_courts, status)` view gives free, booked, no session or not open; SQL tests cover each status and the `window_end()` boundary
- [ ] `save_watches(member, added, removed)` applies the batch (one row per chosen hour, no duplicates, single dates may be after `window_end()`) and returns one new-watch message for slots free now on the added hours only, or nothing
- [ ] The message has the headline, a second line listing the added hours joined by ` · ` (`Weekly Tue 11:00`, `Fri 23 Oct 15:00`), then the usual linked lines; it ignores the 30-minute rule but its slots then count toward it
- [ ] `POST /watches` sends the message, reports the outcome and returns the new state; `GET /state` adds watches, 7 weeks of availability, last check time and `window_end`
- [ ] A basic page lists the member's watches and lets them add or remove hours and save
- [ ] Live demo: saving a watch on a free hour delivers the DM
