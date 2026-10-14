# 04: Delivery rules: 30-minute rule, retries and unreachable members

**What to build:** Members aren't re-alerted about the same Slot within 30 minutes, an alert that failed to send is retried while the slot is still free, and a Member who has blocked the bot is recorded as unreachable rather than retried forever. Spec: Rules (30-minute rule), `mark_sent` / `mark_failed`, Message format (mixed headline), [Decide how the owner learns the notifier is broken](../decisions/11-scraper-health-signal.md) (unreachable members).

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] The same slot (court + date + hour) isn't alerted to the same member again within 30 min; only alerts with `sent_at` count; a slot freed again after 30 min is alerted again
- [ ] Unsent alerts whose slot is still free are retried in the next `record_scan`; after 3 failures they are abandoned
- [ ] `mark_failed` classifies by HTTP status: an alert abandoned with a 403 sets `member.unreachable_since`; any later successful send to that member clears it
- [ ] A message mixing kinds (e.g. a Cancellation plus a retried release alert) uses the `🎾 Free now` headline
- [ ] SQL tests cover flipping within 30 min, re-free after 30 min, retry then abandon, and the 403 set/clear
