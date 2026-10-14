# 08: Sign in with Telegram

**What to build:** an existing Member (the owner, seeded by hand) opens the site on GitHub Pages, logs in with the Telegram widget (which also lets the bot message them), stays signed in and sees an account menu. Someone who isn't a member sees the invite-only screen. Spec: Edge Function API (pure modules, `POST /login`, `GET /state`), `login`, [Prototype the watch-management website](../decisions/08-watch-management-website.md) (sign-in screens).

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] One Supabase Edge Function: pure `verifyTelegramLogin(payload, botToken, now)` (HMAC check, `auth_date` within 24 h) and `sessionToken.sign` / `sessionToken.verify` (30-day expiry), unit-tested with `deno test` (good vector, tampered field, stale or expired)
- [ ] SQL `login(telegram_user, invite_token)` refreshes an existing member's name and username, otherwise returns "not a member" (invite redemption comes in 12); SQL tests cover both
- [ ] `POST /login` and `GET /state` (member and owner flag) wired to the SQL; RLS denies all anonymous access
- [ ] Static site: signed-out screen with the "Log in with Telegram" button (`request_access=write`) and the note that logging in lets the bot message you; the "This one's invite-only… ask Jacopo for an invite link" screen; an account menu with name, handle and Log out
- [ ] Live demo (once 01 is done and the Pages domain is set with BotFather): the owner logs in
