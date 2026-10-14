# 03: Cancellation alerts by Telegram

**What to build:** when a scan sees a watched Slot go from booked to free, the Member gets a Telegram DM like `🎾 Court free` followed by `Wed 14 Oct 10:00  C3`, with each court linking to its court page. This builds the shared match → group → format pipeline that every later message reuses. Spec: Shared SQL functions, Rules (booking window), Message format, Poller orchestration (scan job steps 2–4).

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] `record_scan` returns `(chat_id, text, alert_ids[])` messages for booked → free slots matching a Watch (weekly or single-date), within `window_end()` and not yet started; it writes `alert` rows of kind `cancellation`
- [ ] Booked → missing → free counts as a Cancellation; days after `window_end()` never produce one; past slots are never alerted
- [ ] One message per member per check, lines in date-then-hour order, courts ascending, `C<n>` linked to the court detail page; headline `🎾 Court free` for one slot and `🎾 Courts free` for more
- [ ] The poller sends each message with `parse_mode: HTML` and link previews disabled, then calls `mark_sent` or `mark_failed(alert_ids, http_status, error)`
- [ ] SQL tests assert the exact message text and the resulting rows
- [ ] Live demo (once 01 is done): seed the owner and a watch by hand; a freed slot reaches the owner's Telegram
