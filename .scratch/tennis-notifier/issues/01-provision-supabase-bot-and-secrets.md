# 01: Provision Supabase, the bot and GitHub secrets

**What to build:** the owner has a free Supabase project, a Telegram bot and the GitHub repo secrets, so every later slice can be demonstrated live and not just in tests. This is HITL work: the agent generates a `/wizard` and the owner runs it. Spec: [Deploy and operate](../spec.md#deploy-and-operate-runbook-graduated-from-the-maps-last-fog-patch), steps 1–3 (accounts and secrets only).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Type:** HITL

- [ ] A free Supabase project exists; its URL and service key are stored as GitHub secrets and in a git-ignored local `.env`
- [ ] A Telegram bot exists (BotFather); its token is stored as a GitHub secret and in `.env`. `/setdomain` waits until Pages is live (ticket 14)
- [ ] The owner's Telegram user id is recorded in `.env`, ready for seeding the owner row
- [ ] The wizard can be re-run to rotate any value
- [ ] Nothing secret is committed; the repo stays public
