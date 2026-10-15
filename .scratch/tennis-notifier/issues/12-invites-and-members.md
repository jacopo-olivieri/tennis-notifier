# 12: Invites and members (owner)

**What to build:** the owner creates single-use invite links, shares them, and manages the member list; a friend who opens a link and logs in with Telegram becomes a Member. Spec: `login` (invite redemption), owner-only functions, Edge Function owner endpoints, User Stories 1–2, 6 and 10–15.

**Blocked by:** 08

**Status:** resolved

- [x] `create_invite` returns a raw token once and stores only its hash, with a 7-day expiry; `revoke_invite` revokes it
- [x] `login` with a valid invite token (unused, unexpired, unrevoked) creates the member and marks the invite used; used, expired or revoked tokens return "invite invalid"
- [x] `list_members` (name, handle, hours watched) and `remove_member` (hard delete cascading to watches and alerts); every owner-only function refuses non-owners
- [x] SQL tests cover single use, expiry, revoke, non-owner refusals and the cascade
- [x] The invite landing page says "Jacopo invited you", keeps the token through login and sends it with `POST /login`
- [x] Owner-only Members tab: the member list with Remove, "Create invite link" with copy, and outstanding links with revoke

## Comments

**2026-10-15:** Implemented. Still to do by hand:
1. Apply `supabase/migrations/20261015180000_invites_and_members.sql` in the Supabase SQL editor.
2. Redeploy the function: `npx supabase functions deploy api --project-ref <ref> --no-verify-jwt`. CORS now allows DELETE.
3. Push main so Pages publishes `site/`.
4. Create an invite on the live site and redeem it from a second Telegram account.

- **SQL** (new migration, with 21 tests in `tests/db/test_invites_and_members.py`):
  - The `invite` table stores only the SHA-256 of the token. The token is two `gen_random_uuid()`s (core Postgres, no pgcrypto) and expires 7 days after it's made.
  - `login` now redeems an invite. A stranger with a valid token becomes a Member. One UPDATE claims the invite, so two people racing for it can't both win. Any other token gets `invite_invalid`. A Member who opens an invite just logs in and leaves it unused.
  - `create_invite`, `revoke_invite`, `list_invites`, `list_members` and `remove_member` call `require_owner` and refuse anyone else with SQLSTATE 42501. The owner can't be removed.
  - Hours watched counts the weekly watches plus the single-date ones not yet started.
  - Removing a Member cascades to their watches and alerts. Their used invite keeps `used_at`, but `used_by` is set to null.
- **Edge Function:**
  - `GET /members` returns `{members, invites}`. `POST /invites` returns `{id, token, expires_at}`. `DELETE /members/:id` and `DELETE /invites/:id` complete the set.
  - 42501 becomes 403 `owner_only`. A missing session, or one for a removed Member, gets 401.
- **Spec changes:**
  - `revoke_invite` takes the invite's id, because the site never sees the hash.
  - `list_invites` is added for the outstanding links.
  - `invite` gains `id`, and `login` documents `invite_invalid`.
- **Site:**
  - `site/invites.js` holds pure helpers for the link, reading the token, stripping it, and a member's line, tested with `deno test`.
  - `?invite=` shows "Jacopo invited you". The token goes with `POST /login` and comes off the address once login has used it.
  - A used, expired or revoked link shows "That invite link doesn't work … Ask Jacopo for a new one."
  - The owner gets a third tab, Members. It shows the member list with Remove (after a confirm), "Create invite link" with Copy, and links not used yet with Revoke.
  - A new link shows only until it's revoked or the owner leaves the tab, since it can't be fetched again.
- **Local smoke run.** Setup: headless Brave, the real function in Deno, a fake PostgREST over a scratch Postgres, and widget payloads signed with a test bot token.
  - The owner made two links and revoked one. A friend opened the other, saw "Jacopo invited you", logged in, and the address lost its token.
  - A third account reusing the link got "doesn't work".
  - The owner removed the friend, and the friend's next load was signed out.
  - A non-owner got 403 on all four owner endpoints.
  - No horizontal scroll at 375 px.
- **From the review:**
  - Fixed: the spec's `invite` columns and its `login` wording. The new-link box stayed up after that link was revoked. Opening the Members tab mid-save re-enabled Save. A removed owner got 403, not 401. Duplicated owner-action code. `token_hash()` shadowed the column name.
  - Left:
    - Removing the owner (which the UI never offers) reports `owner_only`.
    - The `20261015000000_login.sql` comment still says invites aren't built. That migration is history, and the new one replaces the function.
    - `housekeep` deleting expired invites is ticket 13.

**2026-10-15:** Live. The owner ran the migration in the SQL editor. `api` was redeployed, and an unsigned `GET /members` gets 401 `signed_out`, with CORS allowing DELETE. Main was pushed as 7d6f925; `test` and `pages` passed. The owner chose not to check redeeming an invite on the live site; that's covered by the local smoke run above.
