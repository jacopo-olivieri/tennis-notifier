# 08: Sign in with Telegram

**What to build:** an existing Member (the owner, seeded by hand) opens the site on GitHub Pages, logs in with the Telegram widget (which also lets the bot message them), stays signed in and sees an account menu. Someone who isn't a member sees the invite-only screen. Spec: Edge Function API (pure modules, `POST /login`, `GET /state`), `login`, [Prototype the watch-management website](../decisions/08-watch-management-website.md) (sign-in screens).

**Blocked by:** 02

**Status:** resolved

- [x] One Supabase Edge Function: pure `verifyTelegramLogin(payload, botToken, now)` (HMAC check, `auth_date` within 24 h) and `sessionToken.sign` / `sessionToken.verify` (30-day expiry), unit-tested with `deno test` (good vector, tampered field, stale or expired)
- [x] SQL `login(telegram_user, invite_token)` refreshes an existing member's name and username, otherwise returns "not a member" (invite redemption comes in 12); SQL tests cover both
- [x] `POST /login` and `GET /state` (member and owner flag) wired to the SQL; RLS denies all anonymous access
- [x] Static site: signed-out screen with the "Log in with Telegram" button (`request_access=write`) and the note that logging in lets the bot message you; the "This one's invite-only… ask Jacopo for an invite link" screen; an account menu with name, handle and Log out
- [x] Live demo (once 01 is done and the Pages domain is set with BotFather): the owner logs in

## Comments

**2026-10-15:** Implemented; the live demo waits on `scripts/sign_in.sh`.

- **SQL** (`supabase/migrations/20261015000000_login.sql`, tested in `tests/db/test_login.py`):
  - `login(telegram_user, invite_token)` refreshes a member's `first_name` and `username` (a dropped username becomes null) and returns `{status: member, member_id}`, otherwise `{status: not_member}`. `invite_token` is accepted and ignored until 12.
  - `member_state(member_id)` is what `GET /state` returns: `{member: {first_name, username, is_owner}}`, or null once the member is removed. Ticket 09 extends it with watches, availability, the last check and `window_end`. It isn't in the spec's function table before this ticket.
  - `test_grants.py` now checks that every public table has RLS on with no policies, so only `service_role` sees rows, and that other roles can't call `login`.
- **Edge Function** `supabase/functions/api/`:
  - Pure modules `telegram_login.ts` and `session_token.ts`, with `deno test`. The good vector was signed by Python's `hmac`, an independent implementation.
  - The session token is `<member_id>.<expires>.<HMAC>`, sent as `Authorization: Bearer`. JWT verification is off for this function (`supabase/config.toml`, and `--no-verify-jwt` on deploy).
  - `POST /login` returns `{session, state}`, 403 `not_member`, or 401 `bad_login` for a bad or stale signature. `GET /state` returns 401 `signed_out` for a missing, forged or expired token, or a removed member. CORS allows any origin, since no cookies are involved.
  - CI runs `deno check` and `deno test` in a second job of `test.yml`.
- **Site** `site/` (`index.html`, `app.js`, `config.js`), styled from the prototype. The button opens Telegram's login popup through `Telegram.Login.auth` with `request_access: write`, so it can keep the prototype's look instead of the widget's iframe. The session stays in `localStorage` for its 30 days. Signed in, there is an account menu (name, @handle, Log out) and a placeholder card until 09.
- **Pages early:** the live demo needs the site on Pages and the domain set with BotFather, both listed in 14. `.github/workflows/pages.yml` publishes `site/`; `scripts/sign_in.sh` turns Pages on, so 14 only has to check it.
- **Local smoke run** (the function in Deno against a fake PostgREST over a scratch Postgres): owner login refreshed the name and returned a session; `/state` with it gave the owner flag; tampered and missing sessions gave 401; a stranger got 403 `not_member`; a forged id, junk body and `{"user": null}` got 401 `bad_login`.
- **From the review:**
  - Fixed: `verifyTelegramLogin` now also rejects a missing `auth_date`, or one more than a minute in the future. The `pages` run the wizard watches is the one it dispatched.
  - Left as judgement calls:
    - Log out only forgets the token in the browser, so a copied token works until it expires. The only way to cancel every session is `scripts/sign_in.sh rotate`, which signs everyone out.
    - `telegram-widget.js` loads from telegram.org without SRI, and it could read the session in `localStorage`. Telegram doesn't publish fixed hashes for it.
    - `Telegram.Login.auth` (the popup behind a custom button) isn't documented as the widget is. If the live demo shows it misbehaving, swap in the widget's own iframe button.
- **Still to do (HITL):** push main, then run `scripts/sign_in.sh` in a terminal. It applies the migration in the SQL editor, deploys the function with `TELEGRAM_BOT_TOKEN` and a new `SESSION_SECRET` (saved to `.env`), turns on Pages, walks through BotFather `/setdomain` (`jacopo-olivieri.github.io`), and ends with the owner logging in.

**2026-10-14:** Live. `scripts/sign_in.sh` applied the migration, deployed `api`, turned on Pages (deploying from Actions) and set the BotFather domain to `jacopo-olivieri.github.io`. The site is at https://jacopo-olivieri.github.io/tennis-notifier/. The owner logged in, and `login()` refreshed the owner row's username (it was null after seeding). The function refuses an unsigned login with 401 `bad_login`. The first `pages` run failed before Pages was on, as expected; the wizard's dispatched run succeeded. For 14: Pages and `/setdomain` are already done.
