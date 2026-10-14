# 04: Delivery rules: 30-minute rule, retries and unreachable members

**What to build:** Members aren't re-alerted about the same Slot within 30 minutes, an alert that failed to send is retried while the slot is still free, and a Member who has blocked the bot is recorded as unreachable rather than retried forever. Spec: Rules (30-minute rule), `mark_sent` / `mark_failed`, Message format (mixed headline), [Decide how the owner learns the notifier is broken](../decisions/11-scraper-health-signal.md) (unreachable members).

**Blocked by:** 03

**Status:** resolved

- [x] The same slot (court + date + hour) isn't alerted to the same member again within 30 min; only alerts with `sent_at` count; a slot freed again after 30 min is alerted again
- [x] Unsent alerts whose slot is still free are retried in the next `record_scan`; after 3 failures they are abandoned
- [x] `mark_failed` classifies by HTTP status: an alert abandoned with a 403 sets `member.unreachable_since`; any later successful send to that member clears it
- [x] A message mixing kinds (e.g. a Cancellation plus a retried release alert) uses the `🎾 Free now` headline
- [x] SQL tests cover flipping within 30 min, re-free after 30 min, retry then abandon, and the 403 set/clear

## Comments

**2026-10-14:** Implemented in `supabase/migrations/20261014180000_delivery_rules.sql`, tested in `tests/db/test_delivery_rules.py`. The owner still needs to apply the migration in the Supabase SQL editor. The poller is unchanged: it already passes the HTTP status to `mark_failed`.

- `sent_in_last_30_min(member, court, date, hour)` is the 30-minute rule, for later producers to reuse. It counts a send exactly 30 minutes ago, so a re-free is alerted only after *more than* 30 minutes (spec story 40). A repeated `mark_sent` keeps the first `sent_at`, so the window doesn't move.
- `pending(alert)` means unsent and fewer than 3 failures. A new Cancellation is skipped for a member who already has a pending alert for that slot; the retry delivers it instead, so nothing is doubled.
- Retries take pending alerts whose slot a complete court in this scan shows free and that haven't started. An alert that has never failed is left alone for 2 minutes, so a send still in flight (another producer, e.g. `record_release` or `save_watches`) isn't doubled, while one whose sender died before reporting is still delivered by the next scan.
- A retry is also held back while the member was sent that slot in the last 30 minutes. It can fire once that has passed if the slot is still free. This only arises once a second producer exists; revisit with ticket 06/09 if it proves noisy.
- `alert_messages` now heads mixed kinds `🎾 Free now`. A message of only `release` or only `new_watch` alerts still has an empty headline; tickets 06 and 09 add those branches. A lone release retry can reach that path once 06 lands, so add the branch there.
- The mixed-headline test inserts a failed `release` alert row by hand, as `record_release` doesn't exist yet. Switch it to `record_release` + `mark_failed` in ticket 06.
