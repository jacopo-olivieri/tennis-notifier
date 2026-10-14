# 01: Provision Supabase, the bot and GitHub secrets

**What to build:** the owner has a free Supabase project, a Telegram bot and the GitHub repo secrets, so every later slice can be demonstrated live and not just in tests. This is HITL work: the agent generates a `/wizard` and the owner runs it. Spec: [Deploy and operate](../spec.md#deploy-and-operate-runbook-graduated-from-the-maps-last-fog-patch), steps 1–3 (accounts and secrets only).

**Blocked by:** None (can start immediately)

**Status:** resolved

**Type:** HITL

- [x] A free Supabase project exists; its URL and service key are stored as GitHub secrets and in a git-ignored local `.env`
- [x] A Telegram bot exists (BotFather); its token is stored as a GitHub secret and in `.env`. `/setdomain` waits until Pages is live (ticket 14)
- [x] The owner's Telegram user id is recorded in `.env`, ready for seeding the owner row
- [x] The wizard can be re-run to rotate any value
- [x] Nothing secret is committed; the repo stays public

## Comments

**2026-10-14:** Done with `scripts/provision.sh` (re-run it to rotate any value).

- GitHub secrets: `TELEGRAM_BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.
- Local `.env` (git-ignored): those three plus `TELEGRAM_BOT_USERNAME` and `OWNER_TELEGRAM_ID`.
- Supabase project `tnhtgeebjpbfdkgnhrzj`, London, free plan. The DB password is in the owner's password manager, not in `.env`.
- Created with "Automatically expose new tables" off and automatic RLS on. Migrations (ticket 02) must explicitly `GRANT` table and function privileges to `service_role`; don't rely on Supabase's default grants.
