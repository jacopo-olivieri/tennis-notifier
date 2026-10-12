# Alert channel options: WhatsApp, Telegram, email

Type: research
Mode: AFK
Status: resolved
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

What does it take, in setup, cost and per-member onboarding, to send alerts by WhatsApp, Telegram and email to 5–20 members, possibly at any hour and possibly in bursts at release time?

- **WhatsApp:** Meta Cloud API (business verification, phone number, template rules, current 2026 per-message pricing for utility templates) versus unofficial free options such as CallMeBot (onboarding steps, reliability, terms).
- **Telegram:** a bot DMing each member versus posting to one group, and how a member links their Telegram account to their website account.
- **Email:** free transactional providers (e.g. Resend, Brevo, Mailgun, SES) with their free-tier limits and deliverability. The same provider would ideally send the magic-link sign-in emails too.

## Answer

Full findings: `docs/research/alert_channel_options.md` on branch `research/alert-channel-options`. In short, the WhatsApp Cloud API needs paid template messages (about £0.016 each, unverified, and alerts risk being classed as marketing) and real setup. CallMeBot is personal-use only. Telegram bot DMs are free, handle bursts, and link through a `t.me/<bot>?start=<token>` deep link. Free email tiers are enough but need a custom domain. These findings were consumed by [Choose the alert channels](07-choose-alert-channels.md), which picked Telegram only. (Closed retroactively on 2026-10-12.)
