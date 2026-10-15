# Spec: Lincoln's Inn Fields court notifier (v1)

Status: ready-for-agent
Map: [Lincoln's Inn Fields court notifier](map.md)

Terms follow `GLOSSARY.md`: Slot, Watch (weekly or single-date), Member, Owner, Invite link, Release drop, Cancellation, Alert, Heads-up, Channel. Each decision below is the collapsed form of a resolved map ticket; the ticket holds the reasoning.

## Problem Statement

Lincoln's Inn Fields has three council tennis courts, booked on Camden Active. The hours people want, especially weekend mornings and weekday evenings, are gone within one to two and a half minutes of the midnight release, and the courts are fully booked for the current week. Courts do come free later: about 1–11 slots a day go from booked to free, mostly when checkout holds expire about 45 minutes after someone took the slot. But nobody can sit refreshing a slow council website (about 7 seconds a page, three courts, six weeks) to catch them. A small group of friends who play there miss slots they would have booked, simply because they didn't know.

## Solution

A free, always-on notifier for an invite-only group of about 5–20 Members. Each Member signs in to a minimal website with Telegram and picks the hours they want to play: weekly hours (e.g. every Tue 18:00) or single dates (e.g. Sat 31 Oct 10:00, even if that date isn't bookable yet). Each chosen hour is a Watch. Any court matches.

The notifier checks Camden Active every 5 minutes by day and every 15 minutes overnight, plus a 10-second burst at the midnight release. When a slot matching someone's Watch becomes bookable, through a Release drop or a Cancellation, the bot sends that Member a short Telegram DM listing the free hours and courts, with a link to each court's page. At 20:00 it sends a Heads-up for hours that should open at midnight. It never books anything; Members book on Camden Active themselves.

The owner learns about outages through an external dead-man's switch, not from the notifier itself.

## User Stories

### Signing in and membership

1. As a prospective member, I want to open an invite link the owner sent me and log in with Telegram, so that I become a member without creating a password.
2. As a prospective member, I want the invite landing page to say who invited me ("Jacopo invited you"), so that I trust the link.
3. As a member, I want logging in with Telegram to also allow the bot to message me, so that there is no separate step to connect alerts.
4. As a member, I want the login button to tell me that logging in lets the bot message me, so that I know what I'm agreeing to.
5. As someone who isn't a member, I want a clear "this one's invite-only, ask Jacopo for an invite link" message after logging in, so that I know why I can't go further.
6. As a prospective member, I want an invite link that has expired, been used or been revoked to be refused clearly, so that I know to ask for a new one.
7. As a member, I want to stay signed in between visits, so that managing watches is quick.
8. As a member, I want an account menu showing my name and Telegram handle with a Log out option, so that I can see who I'm signed in as and leave.
9. As a member, I want my displayed name and handle to update when I change them in Telegram, so that the owner's member list stays accurate.

### Owner

10. As the owner, I want to create a single-use invite link and copy it, so that I can bring a friend in.
11. As the owner, I want to see my outstanding invite links and revoke any of them, so that a link sent to the wrong person can't be used.
12. As the owner, I want unused invite links to expire after 7 days, so that old links lying around in chats stop working.
13. As the owner, I want a Members tab listing each member's name, Telegram handle and number of hours watched, so that I know who is in the group.
14. As the owner, I want to remove a member, so that people who leave the group stop getting alerts; their watches and alert history go with them.
15. As the owner, I want to be the only one who can invite or remove members, so that membership stays under my control.

### Managing watches: weekly

16. As a member, I want a Mon–Sun × hour grid where clicking a cell watches that weekday and hour every week, so that I can describe my regular playing times quickly.
17. As a member, I want each grid cell to show one dot for each of the next 5 weeks (green if any court is free, grey if booked), so that I can see where availability is before choosing.
18. As a member, I want cells for hours with no court that season (e.g. after dusk in winter) shown dashed, so that I don't watch hours that never exist.
19. As a member, I want selecting a cell to show the next five dates for that weekday and hour with which courts are free on each, so that I can see the detail behind the dots.

### Managing watches: single dates

20. As a member, I want a 7-week calendar showing each day's free count, so that I can pick a specific date.
21. As a member, I want clicking a day to show only the hours when a court runs, each marked "N free" or "Booked", so that I can choose an hour on that date.
22. As a member, I want hours already covered by a weekly watch to show "✓ Weekly" and not be clickable, so that I don't create duplicates.
23. As a member, I want hours I already watch to show "✓ Watching", so that I can see my choices at a glance.
24. As a member, I want to watch hours on dates that aren't bookable yet (beyond today + 34), shown as "not open" with the date booking opens, so that I'm ready for the release.
25. As a member, I want single-date watches whose date has passed to disappear quietly, so that my list doesn't fill with stale entries.

### Saving and reviewing

26. As a member, I want my changes to collect in an "N unsaved changes · Discard · Save" bar, so that I can adjust several hours before committing.
27. As a member, I want to discard unsaved changes, so that I can back out of a mistake.
28. As a member, I want one Telegram message right after saving that lists the slots already free for the hours I just added, so that I can book something immediately.
29. As a member, I want that new-watch message to list only the hours added in that save, not everything I watch, so that it isn't noisy.
30. As a member, I want a "Your watches" panel with Weekly and Single dates lists, contiguous hours merged into lines (e.g. "Sat · Sun 08:00–10:00"), each with its current free count and a × to remove it, so that I can review and prune my watches.
31. As a member, I want to stop watching by clicking hours off rather than through a separate pause switch, so that there's only one way to change what I get.
32. As a member, I want a footer showing when the last check ran and the bookable-until date, so that I can trust the data is fresh.
33. As a member, I want the site to remind me that booking stays on Camden Active, so that I don't expect it to book for me.
34. As a member on a phone, I want the same layout stacked, with the weekly detail directly under the grid, so that I can manage watches on mobile.

### Alerts

35. As a member, I want a Telegram DM the moment a slot matching my watch is released at midnight, so that I can race for it.
36. As a member, I want a Telegram DM when a slot matching my watch goes from booked to free, at any hour, so that I can grab cancellations and expired holds.
37. As a member, I want one message per check listing every matching slot, grouped by date and hour with courts listed, so that a release doesn't produce a flood of messages.
38. As a member, I want each court in an alert to link to that court's page on Camden Active, so that I can get to booking in one tap.
39. As a member, I want not to be alerted about the same slot again within 30 minutes, so that a slot flipping while someone holds it doesn't spam me.
40. As a member, I want to be alerted again if a slot frees up after more than 30 minutes, so that I get a second chance when a midnight checkout hold expires about 45 minutes later.
41. As a member, I want no alerts for slots that have already started, so that I'm never told about something I can't use.
42. As a member, I want no alerts for slots beyond the booking window, so that I'm never sent to a slot I can't book.
43. As a member, I want an alert that failed to send to be retried on the next check while the slot is still free, so that a Telegram hiccup doesn't cost me a court.
44. As a member, I want a headline that tells me at a glance what happened ("Just released", "Court free", "Free now"), so that I can decide quickly whether to act.

### Heads-up

45. As a member, I want an evening message at about 20:00 London time listing my watched hours that should open at midnight, so that I can be ready to book.
46. As a member, I want the heads-up to say the slots *should* open and carry no links, so that I'm not misled about hours the venue might block.
47. As a member, I want only one heads-up per evening even if checks run late or repeat, so that I'm not spammed.
48. As a member, I want the heads-up and the midnight alert to work the same in summer and winter time, so that the clock change doesn't break them.

### Reachability

49. As a member who has blocked the bot, I want the website to show a banner "the bot can't message you — unblock it", so that I know why alerts stopped.
50. As a member, I want that banner to disappear once the bot reaches me again, so that it doesn't nag me after I've fixed it.

### Owner operations and health

51. As the owner, I want a Telegram message and an email from Healthchecks.io when regular checks stop succeeding for 30 minutes, so that I learn about a broken scraper, an expired dispatch token, a down database or a revoked bot token.
52. As the owner, I want a separate alarm when the midnight release didn't complete, so that a missed release is caught even though regular checks resume afterwards.
53. As the owner, I want transient Camden errors (520s on one court) not to raise an alarm, so that I'm not woken by noise.
54. As the owner, I want a notice when a check recovers, so that I know the outage is over.
55. As the owner, I want a Camden page-layout change to stop the health pings, rather than being read as "everything booked" or "everything free", so that a broken parser is loud and never produces false alerts.
56. As the owner, I want one court failing to parse not to stop alerts for the other two, so that partial outages degrade gracefully.
57. As the owner, I want a deploy runbook covering every account, secret and scheduled job, so that I can rebuild or rotate anything without rediscovering it.
58. As the owner, I want old data (past slots, past single-date watches, expired invites, logs older than 30 days) cleaned up automatically, so that the free database tier is never exceeded.
59. As the owner, I want everything to run on free tiers and nothing on my Mac, so that it costs nothing and runs when my laptop is off.
60. As the owner, I want member data never committed to the public repo, so that friends' Telegram identities stay private.

### Being a good citizen

61. As the council, I want the notifier to make no more requests than its schedule needs, never run two pollers at once, and leave bookings to people, so that the site isn't burdened.

## Implementation Decisions

### Architecture (from [Choose the hosting architecture](decisions/06-hosting-architecture.md))

- **Poller:** Python 3.12 on GitHub Actions in this public repo; the repo must stay public for free minutes. It is triggered only by `workflow_dispatch` from cron-job.org, using a fine-grained PAT that can only dispatch workflows. GitHub's `schedule` trigger is not used: in testing it fired only about every 3 hours.
- **Two workflows:**
  - `scan`: every 5 min 07:00–23:00 and every 15 min overnight, London time. Runs are serialised by their own concurrency group, and a full scan takes about 3 min.
  - `release`: dispatched twice a night, at 23:45 and 23:50, in its own concurrency group. Exclusion between the release and scan jobs comes from the release claim in the database, not from GitHub concurrency.
- **State:** one free Supabase project (Postgres). All matching, formatting and bookkeeping logic lives in SQL functions, so the Python poller and the TypeScript Edge Function share one source of truth. The poller calls them through Supabase's REST RPC endpoint with the service key, which keeps it stdlib-only like the logger. The Edge Function calls them through supabase-js.
- **Website:** static HTML/JS on GitHub Pages from this repo, with no build step required. Its only API is one Supabase Edge Function. RLS denies all anonymous access; the browser never talks to Postgres directly.
- **Telegram:** outbound only (`sendMessage`), with no webhook and no `getUpdates`. The site's domain is registered with BotFather `/setdomain` for the Login Widget, which runs with `request_access=write`.
- **Retire the logger:** the `observe` workflow, `logger/` and `data/` stop when the notifier goes live. `logger/observe.py` is the source for the scraper code that gets ported.

### Scraper module (Python)

- **Interface:**
  - `parse_week(html)` returns a week start and a map of `(date, hour) → free | booked`. It raises a parse error when the week start or the day structure is missing.
  - `next_week_form(html)` returns the postback form for the next week (all hidden inputs plus `__EVENTTARGET=ctl00$PageContent$btnNextWeek` and an empty `__EVENTARGUMENT`).
  - `scan_court(court)` does a GET, then 5 chained postbacks with cookies kept and about 2 s between requests. It returns the slots plus the number of weeks parsed.
- Both parsing functions are pure, ported from `logger/observe.py`.
- Courts are fixed config:
  - Court 1: detail page 171, event 192
  - Court 2: detail page 176, event 199
  - Court 3: detail page 177, event 200
- A browser User-Agent, stdlib `urllib` only.
- `record_scan` takes per-court results that **carry completeness**: weeks parsed and the slots, or an error. The database decides whether a court is complete, so the poller makes no judgement about it.
- **Release detection** uses the logger's proven probe. Fetch a court page for a session cookie, then request `book.aspx` for the releasing day: a redirect to `login.aspx` means the day is open, a redirect back to the detail page means it isn't. The grid can't detect the release, because it shows "Book" beyond the window.

### Data model (from [Design the Supabase data model and shared matching functions](decisions/09-data-model-and-shared-functions.md))

All dates and hours are London-local (`date` + `hour smallint`).

- `member(id, telegram_id unique, first_name, username, is_owner, joined_at, unreachable_since null)`: name and username are refreshed at every login. The owner row is seeded by hand. Removal is a hard delete that cascades to the member's watches and alerts.
- `invite(id, token_hash, created_at, expires_at, used_by, used_at, revoked_at)`: only the hash of the token is stored. Single use, with a 7-day expiry.
- `watch(member_id, weekday null, date null, hour)`: exactly one of `weekday` and `date` is set, enforced by a check constraint and unique per member. Each chosen hour is one Watch; merged lines are display only.
- `slot(court, date, hour, status, status_since, last_seen_at)`: the snapshot, holding every scanned day including days not yet open. A future slot missing from a complete scan is kept, not deleted, so booked → missing → free still counts as a Cancellation.
- `slot_change(court, date, hour, from, to, at)`
- `alert(id, member_id, court, date, hour, kind, created_at, sent_at null, failures, last_error)`: `kind` is `cancellation`, `release` or `new_watch`.
- `marker(kind, for_date, claimed_by, claimed_at, done_at)`, keyed on `(kind, for_date)`: kinds `release` and `heads_up`, claimed with `INSERT … ON CONFLICT DO NOTHING`.
- `scan_log(at, court, ok, slots, error)`: one row per court per scan attempt.
- View `availability(date, hour, free_courts, status)`: status is free, booked, no session or not open. It is the only thing the site reads for grid data.

### The clock seam

- `london_now()` is the **only** clock. It returns a London-local `timestamp` (not timestamptz) and is marked STABLE. It returns `current_setting('app.now', true)` when that is set, and otherwise `now()` converted to Europe/London.
- `window_end()` returns `london_now()::date + 34`, and is defined in exactly that one function.
- Callers never pass "now". CI fails if `now()`, `current_date`, `current_timestamp` or `localtime` appears in any migration outside `london_now()`.

### Shared SQL functions

Each producer returns ready-to-send messages `(chat_id, text, alert_ids[])`. The caller POSTs each to Telegram, then reports the outcome. All four producers share one internal pipeline:

1. Match Watches to slots.
2. Drop slots already sent to that member in the last 30 minutes.
3. Group by member.
4. Format.

| Function | Caller | Behaviour |
|---|---|---|
| `record_scan(courts jsonb)` | `scan` job | Applies complete courts and logs every court in `scan_log`. Logs status changes. Returns alerts for booked → free slots that are within the window and haven't started, plus retries of unsent alerts whose slot is still free. Also returns whether all 3 courts were complete. |
| `record_release(day)` | `release` job, once the day is open | Returns release alerts for every free slot on that day that matches a Watch, from the latest snapshot. Sets the release marker's `done_at`. |
| `heads_up_due(run_id)` | `scan` job, every run | At or after 20:00, claims the `heads_up` marker for today and returns `{for_date, messages}`: Heads-ups for watched hours on today + 35 where at least one court shows free. Returns nothing if the marker is already done or it's before 20:00. With no messages, the marker is done at once. |
| `mark_heads_up_done(day)` | `scan` job | Sets the `heads_up` marker's `done_at` once the Heads-ups' sends are reported. |
| `save_watches(member, added, removed)` | Edge Function | Applies the batch and returns the single new-watch message for slots free now on the added hours only (empty if there are none). |
| `mark_sent(alert_ids)` | all callers | Sets `sent_at` and clears `unreachable_since`. |
| `mark_failed(alert_ids, http_status, error)` | all callers | Increments `failures`. After 3 failures the alert is abandoned. If it's abandoned with a 403, sets `unreachable_since`. The poller classifies nothing. |
| `claim_release(day, run_id)` | `release` job | Returns whether this run holds the claim. |
| `release_claim_held()` | `scan` job | True while a release claim for tonight exists, has no `done_at` and is before 00:15. The scan exits at once when it's true. |
| `login(telegram_user, invite_token null)` | Edge Function | Refreshes an existing member. Otherwise redeems a valid invite: it must be unused, unexpired and unrevoked, then the invite is marked used and a member is created. Any other invite token returns "invite invalid"; no token returns "not a member". |
| `member_state(member_id)` | Edge Function | What `GET /state` returns for a signed-in member, or null once they've been removed. |
| `create_invite(owner)`, `revoke_invite(owner, invite_id)`, `list_invites(owner)`, `list_members(owner)`, `remove_member(owner, member)` | Edge Function | Owner-only; anyone else gets SQLSTATE 42501, which the Edge Function returns as 403. `create_invite` returns the raw token once. `list_invites` lists the links that are still usable. `list_members` counts as hours watched the weekly watches and the single-date ones not yet started. The owner can't be removed. |
| `housekeep()` | `pg_cron` daily at ~03:00 London | Deletes past single-date watches, past slots, expired invites, and alert, slot_change and scan_log rows older than 30 days. A plain function, so it's testable without pg_cron. |

**Rules encoded in these functions:**
- **Complete court:** all 6 weeks parsed, and at least 50% of the slots that court had last time. Otherwise the court is logged as failed, its stored slots are left untouched, and its diff is skipped.
- **30-minute rule:** applies per slot (court + date + hour). Only alerts with `sent_at` set count. The new-watch alert ignores the rule, but its slots count toward it afterwards.
- **Booking window:**
  - A slot after `window_end()` is "not open" and never produces a Cancellation.
  - A slot crossing into the window at midnight with its status unchanged produces nothing from `record_scan`; only `record_release` alerts for it.
  - Past slots are never alerted.
- **Heads-up marker:** set done only after its sends are reported.

### Message format (from [Draft the alert and heads-up messages](decisions/10-alert-and-heads-up-wording.md))

Telegram `sendMessage` with `parse_mode: HTML`, link previews disabled, no inline keyboard and no footer. The message is a bold headline, a blank line, then one line per date and hour in date-then-hour order: `Sun 22 Nov 09:00  C1 C2 C3`.
- The date has no year, the time is 24-hour London time, and there are two spaces before the courts.
- Courts are in ascending order. In alerts each `C<n>` links to its court detail page; Heads-ups have no links.

| Message | Headline |
|---|---|
| Release drop | `🎾 Just released` |
| Cancellation | `🎾 Court free` for one slot, `🎾 Courts free` for more |
| Mixed kinds in one check | `🎾 Free now` |
| A new-watch alert retried by a later check (its first send failed) | `🎾 Free now` |
| New watch | `🎾 Free now for your new watches`, plus a second line listing the added hours joined by ` · ` (`Weekly Tue 11:00`, `Fri 23 Oct 15:00`) |
| Heads-up | `🌙 Opens at midnight` |

### Poller orchestration (Python)

**`scan` job:**
1. If `release_claim_held()`, exit.
2. Scan the 3 courts.
3. `record_scan`.
4. Send the returned messages and report each outcome.
5. `heads_up_due(run_id)`, send, then `mark_heads_up_done`.
6. Ping the Healthchecks `scan` URL if `should_ping` allows it.

**`release` job:**
1. `claim_release(today + 35)`; exit if the claim isn't held.
2. Sleep until 23:59:30.
3. Probe the releasing day every ~10 s until it's open.
4. `record_release`.
5. Send and report.
6. Ping the Healthchecks `release` URL.

**Health predicate:** `should_ping(scan_result, send_outcomes)` is a pure function. It is true only when `record_scan` succeeded, all 3 courts were complete, and no send returned 401. A 403 from one member doesn't block the ping. Pings go after the sends, so a revoked token withholds them.

A run fails its GitHub job only on unexpected errors. The health signal is Healthchecks, not job status.

### Edge Function API (TypeScript/Deno)

**Pure modules:**
- `verifyTelegramLogin(payload, botToken, now)` checks the HMAC-SHA256 of the data-check string, keyed by SHA-256 of the bot token, and rejects an `auth_date` older than 24 h.
- `sessionToken.sign` and `sessionToken.verify` produce and check an HMAC-signed token of `member_id` and expiry with a separate session secret, valid for 30 days.

**Endpoints:** everything else is thin wiring to the SQL functions.
- `POST /login`, with the widget payload and an optional invite token. Returns a session, or "not a member", or "invite invalid".
- `GET /state`, returning:
  - the member and whether they're the owner
  - their watches
  - availability for the next 7 weeks
  - `unreachable_since`
  - the last check time
  - `window_end`
- `POST /watches` with `{added, removed}`. Sends the new-watch message (if any) to Telegram, reports the outcome, and returns the new state.
- Owner only: `GET /members` (the members and outstanding invites), `DELETE /members/:id`, `POST /invites`, `DELETE /invites/:id`.

The invite landing URL carries the raw token in its query string. The site keeps the token through the login and sends it with `POST /login`.

### Health monitoring (from [Decide how the owner learns the notifier is broken](decisions/11-scraper-health-signal.md))

Healthchecks.io free plan with two checks:

| Check | Schedule (Europe/London) | Grace |
|---|---|---|
| `scan` | The cron-job.org schedule | 30 min |
| `release` | Daily at 00:00 | 20 min |

Both checks notify only the owner, through Healthchecks' own Telegram integration with email as a backup. The notifier never reports on itself.

### Secrets

| Where | What |
|---|---|
| GitHub secrets | Bot token, Supabase URL, Supabase service key, the two Healthchecks ping URLs |
| Edge Function | Bot token, session secret (the service role is built in) |
| cron-job.org | The dispatch PAT |

Nothing about members is stored in the repo.

### Deploy and operate (runbook; graduated from the map's last fog patch)

1. **Bot:** create it with BotFather and save the token. Once Pages is live, set `/setdomain` to the Pages domain.
2. **Supabase:**
   - Create the project.
   - Apply the SQL migration.
   - Seed the owner's member row with their Telegram id and `is_owner`.
   - Enable `pg_cron` and schedule `housekeep()` daily at 03:00 London time. pg_cron runs in UTC, so schedule it at 02:00 UTC, which gives 03:00 in winter and 03:00–04:00 in summer.
   - Deploy the Edge Function with its secrets.
3. **GitHub:** add the repo secrets. Enable Pages for the site. Disable and remove the `observe` workflow, and stop `data/` commits.
4. **Healthchecks.io:** create the `scan` and `release` checks with the schedules and grace periods above. Connect the Telegram and email integrations. Put the ping URLs in GitHub secrets.
5. **Dispatch PAT:** a fine-grained token scoped to this repo with Actions write only, at the maximum expiry.
6. **cron-job.org:** create jobs dispatching `scan` every 5 min 07:00–23:00 and every 15 min 23:00–07:00, and `release` at 23:45 and 23:50, all in the Europe/London timezone.
7. **Smoke test:**
   - Dispatch `scan` by hand and confirm slots appear and the `scan` check goes green.
   - Log in as the owner, create an invite, redeem it from a second Telegram account, and save a watch on a free hour. The new-watch DM should arrive.
   - Watch the first midnight release live.
8. **Rotating the PAT:** before it expires (GitHub sends an expiry email), create a new one and replace it in cron-job.org. The `scan` check catches a missed rotation.

## Testing Decisions

**What a good test is:** it checks external behaviour at a seam, meaning the messages a function returns and the rows it leaves behind. It doesn't check internal helpers or query shapes, and it should survive a rewrite of the internals.

**Seams (three, reviewed by a second opinion):**

1. **SQL functions against a real Postgres. This is the main seam.** Tests are written in pytest with psycopg, and CI runs them in a GitHub Actions job with a plain `postgres:16` service container and the migrations applied with `psql`. Locally, the Supabase CLI or any Postgres works.
   - Each test runs in one transaction that rolls back, and pins the clock with `set_config('app.now', …, true)`.
   - Migrations must not depend on Supabase-only features: RLS policies don't reference `auth.*`, and pg_cron is only scheduled in the runbook.
   - **Clock boundaries**, which matter most:
     - At 23:59 versus 00:00:10, a not-open slot entering the window with its status unchanged gives no alert from `record_scan`; `record_release` alerts for it.
     - The release claim lapses at 00:15.
     - The heads-up fires at 20:00 but not at 19:59, and only once.
     - The 25 Oct 2026 BST→GMT night.
     - Past slots and single-date watches.
   - **Scan rules:**
     - Booked → free alerts once.
     - Flipping within 30 min doesn't re-alert; a re-free after 30 min does.
     - Booked → missing → free counts as a Cancellation.
     - A court with 5 of 6 weeks, or below 50% of its slots, is skipped and logged while the other courts still apply.
     - Days beyond `window_end` never produce Cancellations.
   - **Delivery:**
     - An unsent alert is retried while the slot is still free and abandoned after 3 failures.
     - A 403 sets `unreachable_since` and a later send clears it.
     - The new-watch alert ignores the 30-minute rule but feeds it afterwards.
   - **Formatting:** exact text for each headline variant, line order, court links present in alerts and absent in Heads-ups, and the new-watch second line.
   - **Membership:** invite single use, expiry, revoke, not-a-member, owner-only refusals, and cascading removal.
   - **`housekeep()`:** deletes exactly what is past or older than 30 days.
2. **Scraper parsing (Python, pure).** Tests cover `parse_week` against the saved sample pages in `docs/research/` and a deliberately broken page, which must raise a parse error. `next_week_form` is tested against a saved page, checking it carries every hidden input and the next-week target. These are ported from the logger's regexes; there is no prior test art.
3. **Poller and Edge Function pure helpers.**
   - `should_ping`: all complete with no 401, one court incomplete, a 401 present, a 403 only.
   - `verifyTelegramLogin` with `deno test`: a known-good vector, a tampered field, a stale `auth_date`.
   - Session token: sign then verify, a tampered token, an expired token.
   - The site's `watches.js` with `deno test` (added in ticket 10): the five weeks behind a grid cell, dashed cells, the grid's hours, merged watch lines with their free counts, and the save batch. Ticket 11 added the Single dates calendar, a day's hours, the booking-open date and hiding past single-date watches.

**Not automated, by choice:**
- The orchestration glue and Edge Function HTTP wiring: a manual smoke test.
- The static website's rendering and clicks: checked by hand against the prototype.
- The midnight sleep and burst timing: observed live on the first night.

The SQL seam already covers everything this glue calls.

**Prior art:** none in the repo; `logger/observe.py` is untested. The two prototypes are the reference for site and message behaviour:
- `prototype/watch-website`: `site/prototype/watches_prototype.html`, v2
- `prototype/alert-wording`: `PROTOTYPE-alert-wording.html`

## Out of Scope

- Auto-booking, or storing members' Camden credentials.
- A public service; membership is invite-only.
- Venues other than Lincoln's Inn Fields, including others on Camden Active.
- Email and WhatsApp alerts; Telegram is the only Channel.
- Quiet hours, muting or a pause switch.
- Inbound bot commands (no webhook, no `/start`).
- A near-start cutoff for Cancellations (cheap to add later).
- In-app outage reporting to members or the owner, beyond the unreachable banner.

## Further Notes

- **Defaults chosen while writing this spec**, not made in tickets, so revisit them freely:
  - session lifetime of 30 days
  - Telegram `auth_date` freshness of 24 h
  - link previews disabled
  - separate GitHub concurrency groups for `scan` and `release`
  - pg_cron at 02:00 UTC
- **Verify on first deploy:** the `book.aspx` probe (login redirect means open) was what the logger used to time releases, but [the platform notes](../../docs/research/camden_active_platform.md) record a later signed-out test where every slot redirected to the detail page. Those tests probably differed in whether a session cookie was fetched first. Confirm the probe distinguishes open from not-open before the first midnight. If it doesn't, the `release` job can fall back to calling `record_release` at 00:00:15, since releases were seen landing between 23:59:55 and 00:00:15.
- **Seasonal hours:** opening hours shrink with dusk (08:00–15:00 in November). Hours with no session simply aren't in the grid, which the `availability` view reports as "no session".
- **Polite polling:** a full scan is about 18 requests spaced about 2 s apart, around 230 scans a day, with exactly one poller at a time guaranteed by the release claim and serialised scans.
- **Decision tickets 01–11** live in `decisions/`, so `issues/` is free for the implementation tickets from `/to-tickets`.
