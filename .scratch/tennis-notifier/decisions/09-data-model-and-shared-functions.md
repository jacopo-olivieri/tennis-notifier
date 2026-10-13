# Design the Supabase data model and shared matching functions

Type: grilling
Mode: HITL
Status: resolved
Blocked by: 08
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

What tables, columns and SQL functions does Supabase hold so that the poller and the Edge Function share one source of truth? Cover:
- members and invites
- watches, both recurring and one-off
- the slot snapshot and how a scan is compared with it to detect release drops and cancellations (booked → free)
- the alert log behind the 30-minute no-repeat rule
- the release-claim and heads-up markers
- the signatures of the shared "match a watch" and "format and record an alert" functions

Also: what happens when a scan is partial or fails midway, so that a half-scan doesn't produce a burst of false "free" changes?

Context: [Choose the hosting architecture](06-hosting-architecture.md).

## Comments

- 2026-10-12: From [Prototype the watch-management website](08-watch-management-website.md):
  - A watch is a set of chosen hours, not a window: weekly (weekday + start hour) and single-date (date + start hour) rows. "Sat · Sun 08:00–10:00" is only how the site displays them.
  - Single-date hours may be later than today + 34 (they need the heads-up). Past ones are deleted quietly.
  - Invites are single-use tokens with a 7-day expiry, plus revoke. There is one owner, who can remove members (their watches go with them).
  - A save is a batch of added and removed hours. The new-watch alert covers only the slots matched by hours added in that save.
  - The site needs, per weekday and hour, the next 5 weeks' status (free / booked / no session) and the free courts per date and hour, both read from the snapshot.
  - Data issue: the current snapshot has "free" slots after today + 34 (up to 22 Nov on 12 Oct). These are probably not bookable yet, so the scan or the snapshot must cut at the booking window, or a not-yet-open day will look like a cancellation or release.

## Answer

Decided with the owner on 2026-10-12. Terms follow `GLOSSARY.md`. All dates and hours are London-local (`date` + `hour smallint`), and the database clock is the only clock: callers never pass "now".

**Tables**
- `member(id, telegram_id unique, first_name, username, is_owner, joined_at)`: name and username are refreshed at every login. The owner is flagged by hand once. Removing a member is a hard delete that cascades to their watches and alerts.
- `invite(token_hash, created_at, expires_at, used_by, used_at, revoked_at)`: only a hash of the token is stored. Single use, 7-day expiry.
- `watch(member_id, weekday null, date null, hour)`: exactly one of weekday and date is set. **Each chosen hour is one Watch.** The site's merged lines are only display.
- `slot(court, date, hour, status, status_since, last_seen_at)`: the snapshot, with `status` set to `free` or `booked` exactly as the HTML shows it. Every scanned day is stored, including days not open yet. A future slot missing from a complete scan is **kept** (stale `last_seen_at`), never deleted, so `booked → missing → free` still counts as a cancellation. Past slots are pruned.
- `slot_change(court, date, hour, from, to, at)`: every status change, kept 30 days.
- `alert(id, member_id, court, date, hour, kind, created_at, sent_at null, failures, last_error)`: `kind` is one of cancellation, release or new_watch. Kept 30 days.
- `marker(kind, for_date, claimed_by, claimed_at, done_at)`, keyed on `(kind, for_date)`: `release` and `heads_up`, claimed with `INSERT … ON CONFLICT DO NOTHING`.
- `scan_log(at, court, ok, slots, error)`: one row per court per scan attempt, kept 30 days. How it's used is left to [Decide how the owner learns the notifier is broken](11-scraper-health-signal.md).
- View `availability(date, hour, free_courts, status)`: status is free, booked, no session or not open. The Edge Function reads only this view for the grid.

**Booking window.** `window_end()` = London today + 34, defined in exactly one SQL function. Days after it are stored but count as "not open". They never produce cancellation alerts, and the site shows them as not open. This settles the data issue in the comments.

**Partial scans.** Each court is applied or skipped on its own. A court is complete only if all 6 weeks parsed and it returned at least 50% of the slots it had last time. Otherwise it's a parse failure: it's logged in `scan_log`, its stored slots are left untouched, and its diff is skipped. One court's 520 doesn't blind the other two, and a half-scan can't create mass "missing" or false "free".

**Shared functions.** Each one returns ready-to-send messages `(chat_id, text, alert_ids[])`. The caller POSTs each message to Telegram, then reports the outcome.

| Function | Caller | Does |
|---|---|---|
| `record_scan(courts jsonb)` | poller, every scan | Applies complete courts, logs changes, and returns alerts for booked → free slots within the window that haven't started yet, plus retries of unsent alerts whose slot is still free |
| `record_release(day)` | midnight job, once `book.aspx` shows the day open | Returns alerts for every free slot on that day that matches a watch, using the latest snapshot. Sets the release marker's `done_at` |
| `heads_up_due()` | first scan at or after 20:00 | Returns heads-ups for the next release day (today + 35), listing watched hours where at least one court shows free. Returns nothing if the `heads_up` marker is done |
| `save_watches(member, added, removed)` | Edge Function, on Save | Applies the batch and returns the single new-watch message, listing currently free slots for the added hours only |
| `mark_sent(alert_ids)` / `mark_failed(alert_ids, error)` | all callers | Records the delivery outcome; the heads-up marker is set done only after its sends succeed |

All four producers share one internal step: match watches → drop slots sent to that member in the last 30 min → group by member → format. The message text is a placeholder until [Draft the alert and heads-up messages](10-alert-and-heads-up-wording.md) decides it.

**30-minute rule.** It applies per slot (court + date + hour). Only alerts with `sent_at` set count. Unsent alerts are retried by the next check while the slot is still free, and abandoned after 3 failures (e.g. a 403 because the member blocked the bot). The new-watch alert **ignores** the rule, since the member just asked, but its slots then count toward it.

**Release claim.** The `release` claim is a lease that lapses at 00:15 London time. After that, regular scans resume whether or not `done_at` is set, and a release without `done_at` is a health signal.

**Housekeeping.** Supabase `pg_cron` runs once a day at ~03:00. It deletes past single-date watches, past slots, expired invites, and alert, change and scan logs older than 30 days.

