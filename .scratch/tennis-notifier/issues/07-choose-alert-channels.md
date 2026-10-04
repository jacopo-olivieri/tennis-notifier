# Choose the alert channels

Type: grilling
Mode: HITL
Status: resolved
Blocked by: 03
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Which channels does v1 offer (Telegram, email, WhatsApp), and how does a member connect each one to their account? Is WhatsApp in or out, given what [Alert channel options: WhatsApp, Telegram, email](03-alert-channel-options.md) finds?

## Comments

- 2026-10-04: The owner chose a Telegram bot as the alert channel, after reading [Alert channel options: WhatsApp, Telegram, email](03-alert-channel-options.md) (findings on branch research/alert-channel-options). Still open: whether email remains a second channel, which decides whether a custom domain (~£10/yr) is needed. This also affects sign-in: email magic link versus Telegram login.

## Answer

**Telegram only.** Alerts go out as Telegram bot DMs, which are free and handle bursts (about 30 messages a second). A member links their account by tapping a one-time `t.me/<bot>?start=<token>` link. Website sign-in also uses Telegram (the Telegram Login Widget) rather than an email magic link, so v1 needs no email sending and no custom domain.

WhatsApp is out: the official API charges per message and needs real setup, and the free unofficial route is personal-use only with no guarantees. Email is out: members are expected to use Telegram, and dropping it avoids the domain cost.
