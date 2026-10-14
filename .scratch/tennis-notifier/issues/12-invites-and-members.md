# 12: Invites and members (owner)

**What to build:** the owner creates single-use invite links, shares them, and manages the member list; a friend who opens a link and logs in with Telegram becomes a Member. Spec: `login` (invite redemption), owner-only functions, Edge Function owner endpoints, User Stories 1–2, 6 and 10–15.

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] `create_invite` returns a raw token once and stores only its hash, with a 7-day expiry; `revoke_invite` revokes it
- [ ] `login` with a valid invite token (unused, unexpired, unrevoked) creates the member and marks the invite used; used, expired or revoked tokens return "invite invalid"
- [ ] `list_members` (name, handle, hours watched) and `remove_member` (hard delete cascading to watches and alerts); every owner-only function refuses non-owners
- [ ] SQL tests cover single use, expiry, revoke, non-owner refusals and the cascade
- [ ] The invite landing page says "Jacopo invited you", keeps the token through login and sends it with `POST /login`
- [ ] Owner-only Members tab: the member list with Remove, "Create invite link" with copy, and outstanding links with revoke
