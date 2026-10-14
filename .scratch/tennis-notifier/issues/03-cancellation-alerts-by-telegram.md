# 03: Cancellation alerts by Telegram

**What to build:** when a scan sees a watched Slot go from booked to free, the Member gets a Telegram DM like `🎾 Court free` followed by `Wed 14 Oct 10:00  C3`, with each court linking to its court page. This builds the shared match → group → format pipeline that every later message reuses. Spec: Shared SQL functions, Rules (booking window), Message format, Poller orchestration (scan job steps 2–4).

**Blocked by:** 02

**Status:** ready-for-agent

- [x] `record_scan` returns `(chat_id, text, alert_ids[])` messages for booked → free slots matching a Watch (weekly or single-date), within `window_end()` and not yet started; it writes `alert` rows of kind `cancellation`
- [x] Booked → missing → free counts as a Cancellation; days after `window_end()` never produce one; past slots are never alerted
- [x] One message per member per check, lines in date-then-hour order, courts ascending, `C<n>` linked to the court detail page; headline `🎾 Court free` for one slot and `🎾 Courts free` for more
- [x] The poller sends each message with `parse_mode: HTML` and link previews disabled, then calls `mark_sent` or `mark_failed(alert_ids, http_status, error)`
- [x] SQL tests assert the exact message text and the resulting rows
- [ ] Live demo (once 01 is done): seed the owner and a watch by hand; a freed slot reaches the owner's Telegram

## Comments

**2026-10-14:** Implemented in the commit that adds `supabase/migrations/20261014120000_cancellation_alerts.sql`. The live demo is still open: the owner needs to apply that migration in the Supabase SQL editor, then seed their `member` row and a watch.

- The shared pipeline is `watched_by(date, hour)` (match) and `alert_messages(alert_ids)` (group and format). `court_page()` repeats the URLs in `COURTS` in `notifier/scraper.py`.
- `alert_messages` builds a headline only when every alert is a cancellation. Any other kind gets a NULL headline (`<b></b>`), so ticket 04's mixed headline and the release headline must add their branches there.
- `mark_sent`/`mark_failed` return void, so PostgREST answers 204 with no body; `rpc()` now returns None for that.
- The send path was checked live: a SQL-formatted sample reached the owner (200), and a bad chat id came back as `400 Bad Request: chat not found`.
- The poller logs no message text or chat ids, because the repo's Actions logs are public.
