# 09: Save watches and the new-watch alert

**What to build:** a signed-in Member adds and removes watched hours (weekly or single-date) and saves them as one batch, and immediately gets one `🎾 Free now for your new watches` DM listing the slots already free for the hours added in that save. The UI here is a plain list; the week grid comes in 10. Spec: `save_watches`, `availability` view, `POST /watches`, Message format (new watch).

**Blocked by:** 03, 08

**Status:** ready-for-agent

- [x] The `availability(date, hour, free_courts, status)` view gives free, booked, no session or not open; SQL tests cover each status and the `window_end()` boundary
- [x] `save_watches(member, added, removed)` applies the batch (one row per chosen hour, no duplicates, single dates may be after `window_end()`) and returns one new-watch message for slots free now on the added hours only, or nothing
- [x] The message has the headline, a second line listing the added hours joined by ` · ` (`Weekly Tue 11:00`, `Fri 23 Oct 15:00`), then the usual linked lines; it ignores the 30-minute rule but its slots then count toward it
- [x] `POST /watches` sends the message, reports the outcome and returns the new state; `GET /state` adds watches, 7 weeks of availability, last check time and `window_end`
- [x] A basic page lists the member's watches and lets them add or remove hours and save
- [ ] Live demo: saving a watch on a free hour delivers the DM

## Comments

**2026-10-14:** Implemented; the live demo is still to do (see the end of this comment).

- **SQL** (`supabase/migrations/20261015120000_save_watches.sql`, tested in `tests/db/test_availability.py` and `test_save_watches.py`):
  - The `availability` view has one row per scanned date and hour that hasn't started yet. Its hours are the ones any court runs on some day, so an hour missing on one day shows as `no session`. Days after `window_end()` show as `not open` with no free courts, unless no court runs that hour (then `no session`), so ticket 11 can still list a not-open day's hours. The view uses `security_invoker`, so it can't get round RLS. Anon is revoked, and a test checks this.
  - `save_watches(member_id, added, removed)` runs `removed`, then `added`. An hour in both batches is left as it was, with no message. A single-date hour that has already started is quietly skipped. The message lists only the hours this save actually inserted. It skips slots that already have a pending alert, so a retry never lists a court twice.
  - `alert_messages(ids, added text default null)` replaces the one-argument version. When `added` is set, the headline is the new-watch one and `added` goes on the second line. A new-watch alert whose send failed is retried by `record_scan` under `🎾 Free now`; the spec's message table now says so.
  - `member_state` now also returns `watches`, `availability` for today to today + 48, `unreachable_since`, `last_check` (the most recent successful court in `scan_log`) and `window_end`.
- **Edge Function:** `POST /watches {added, removed}` returns `{alert: sent | failed | none, state}`. A body that isn't two arrays, or an hour the table refuses (SQLSTATE 22/23), gets 400. `telegram.ts` mirrors `notifier/telegram.py` and has `deno test`s with a fake fetch.
- **Site:** a plain "Your watches" card. It has a list with ×, an add row (Every week / One date, then the weekday or date, then the hour), a pending count with Discard and Save, and a note after saving. The hour menu shows the hours `availability` reports a session for, or 07–21 before the first scan. Ticket 10 replaces it with the grid.
- **Local smoke run** (the function in Deno, a fake PostgREST over a scratch Postgres, Telegram given a bogus token): saving a free hour created `new_watch` alerts, and the failed send recorded `401 Unauthorized`. A save with nothing free returned `none`. A removed member got 401, a bad body or weekday 8 got 400. A headless browser at 375 px showed adding, removing and saving work.
- **From the review:**
  - Fixed: started hours today, remove-and-re-add in one batch, a duplicate alert for a slot already pending, 400s for bad hours, and a dead CSS rule.
  - Left for ticket 11: `availability` only covers scanned days, about 6 weeks, so the 7-week calendar's last ~10 days have no rows yet. Ticket 11 can extend the view with a date series that reports `not open`.
  - Left as judgement calls:
    - The hour and date formatting (`lpad(hour…)`, `to_char(date, 'Dy FMDD Mon')`) is now repeated in three SQL functions and in `app.js`.
    - If `mark_sent` or `mark_failed` fails after a save, the reply is a 500 even though the watches were saved.
    - `POST /watches` builds the member's state twice: once to check the member still exists, once for the reply.
- **Still to do (HITL):**
  1. Apply the migration in the Supabase SQL editor.
  2. Deploy the function: `npx supabase functions deploy api --project-ref <ref> --no-verify-jwt`.
  3. Push main so Pages publishes `site/`.
  4. On the site, save a watch on an hour that's free now and check that the DM arrives.
