# Alert channel options: WhatsApp, Telegram, email

Research for ticket `03-alert-channel-options`, done on 2026-10-04 against vendor docs and pricing pages. Assumptions: 5–20 members, alerts at any hour, and bursts when a release drop matches many watches at once. Claims marked **[unverified]** come only from secondary sources, or the primary page didn't show them when fetched.

## WhatsApp

### Option A: Meta WhatsApp Cloud API (official)

**Setup steps** ([get started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)):
1. Register as a Meta developer and create an app with the "Connect with customers through WhatsApp" use case.
2. Pick or create a business portfolio. A WhatsApp Business Account (WABA) is created with it.
3. Send test messages from the provided test number. The page we fetched didn't give the test number's recipient cap. Older docs said 5 numbers **[unverified]**.
4. Add a real phone number that isn't already registered on a personal WhatsApp account, and add a payment method.
5. Create a system user and generate a permanent token with `business_management`, `whatsapp_business_messaging` and `whatsapp_business_management`.
6. Create a message template and wait for review. "Review can take up to 24 hours" ([templates](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates)).

Business verification doesn't seem to be required to start. New portfolios have a "messaging limit of 250" unique recipients per 24 h, which is plenty for 20 members ([messaging limits](https://developers.facebook.com/docs/whatsapp/messaging-limits)).

**Cost:**
- Pricing has been per message since 1 July 2025 ([pricing](https://developers.facebook.com/docs/whatsapp/pricing)).
- Our alerts are business-initiated and usually fall outside the 24 h customer-service window, so each one is a **paid template message**. The docs say "Utility template messages sent outside of a CSW are charged".
- The UK rate card is only an interactive tool on the [pricing page](https://whatsappbusiness.com/products/platform-pricing/) and wasn't readable when fetched. Secondary sources give **UK utility ≈ £0.0159 per message** **[unverified]** ([whautomate](https://whautomate.com/whatsapp-business-api-pricing-uk), [sleekflow](https://sleekflow.io/en-gb/blog/whatsapp-business-price)).
- **Category risk.** To count as utility, a template "Must be non-promotional" and "specific to or requested by the user… OR essential or critical to the user" ([template guidelines](https://developers.facebook.com/docs/whatsapp/updates-to-pricing/new-template-guidelines)). A "slot now available, book here" alert is user-requested, but Meta could classify it as marketing: back-in-stock and retargeting alerts "are marketing even if requested by users". Marketing rates are higher. The exact UK marketing rate is **[unverified]**.
- **Change effective 1 Oct 2026.** Several BSP sources say service (free-form, in-window) messages are now charged at the utility rate after 1,000 free per business number per month. They also say utility templates sent inside the window are now charged, and that delivery stops without a payment method on file ([360dialog](https://360dialog.com/blog/whatsapp-service-message-charging-october-2026/), [Gupshup](https://support.gupshup.io/hc/en-us/articles/62362400519705-WhatsApp-Service-Messages-Pricing-w-e-f-01-Oct-2026)). **[unverified]**: the Meta developer pages fetched today still say service messages are free and in-window utility is free. Either the pages are stale or the BSPs are wrong.
- **Estimate:** 20 members × ~3 alerts/day × 30 days ≈ 1,800 messages/month, about **£29/month** at £0.0159. A quiet month with ~300 messages is about £5. This is the only option here that isn't free, and a card is required.

**Per-member onboarding:** the member gives their phone number and opts in. WhatsApp policy requires opt-in before business-initiated messages. The policy page URL we tried returned 404, so the exact wording is **[unverified]**.

**Reliability and gotchas:**
- Delivery itself is reliable.
- Overhead is high: you need a separate phone number, template approval, a token to manage and a Meta billing account.
- Free-form alert text isn't possible. Every alert must fit the approved template's variables.
- Meta can recategorise a template, which would change its price.

### Option B: CallMeBot (unofficial, free)

From the [CallMeBot WhatsApp page](https://www.callmebot.com/blog/free-api-whatsapp-messages/) and [FAQ](https://www.callmebot.com/faq/):
- **Onboarding:** each member saves +34 644 05 92 17 as a contact and sends it "I allow callmebot to send me messages". They get a personal API key, usually within 2 minutes ("retry after 24 hours" if not), and paste it into our site.
- **Sending:** `GET https://api.callmebot.com/whatsapp.php?phone=…&text=…&apikey=…`. The notifier stores a phone and API key per member.
- **Terms:** "The Free API is only for personal use." The FAQ says "You can only send messages to yourself". This works only because each member registers their own key. Using it for a 20-person group stretches the "personal use" term **[interpretation]**.
- **Reliability:** no rate limits are published, there's no SLA, text only, and no replies. The service runs on a shared WhatsApp number that WhatsApp could ban or rate-limit. Anecdotal reports of number changes and outages are **[unverified]**.
- **Cost:** free.

## Telegram

The Bot Platform "is free for both users and developers" ([bots intro](https://core.telegram.org/bots)).

**Setup steps:** message @BotFather, run `/newbot`, choose a name and a username ending in `bot`, and get a token ([features](https://core.telegram.org/bots/features)). Send with `sendMessage(chat_id, text)`, which also takes optional `parse_mode`, `link_preview_options` and `disable_notification` ([Bot API](https://core.telegram.org/bots/api)). Updates can come by webhook or `getUpdates`, not both, and Telegram keeps unfetched updates for 24 hours. A cron-only host can poll `getUpdates` and needs no public webhook.

**Rate limits** ([FAQ](https://core.telegram.org/bots/faq)): under 1 message per second per chat, 20 messages per minute per group, and about 30 messages per second overall. A 20-member burst is fine. Batch several matches into one message per member anyway.

### Bot DMs each member (recommended)
- "Bots can't start conversations with users. A user must either add them to a group or send them a message first" ([bots intro](https://core.telegram.org/bots)).
- **Linking accounts with a deep link:**
  1. The website shows `https://t.me/<bot>?start=<token>`. The token is one-time and random, up to 64 chars from `A-Z a-z 0-9 _ -` ([features: deep linking](https://core.telegram.org/bots/features)).
  2. The member taps the link and presses Start, and the bot receives `/start <token>`.
  3. The backend maps the token to the member and stores the `chat_id`.
  4. Onboarding is two taps, and no phone number is shared.
- An alternative is the Telegram Login Widget, which needs `/setdomain` on BotFather to pair the bot with the site. It's more work than a deep link.
- Each member gets only their own alerts. Each can mute the bot or set Do Not Disturb per chat.
- **Gotcha:** if a member blocks the bot, sends fail with an error (commonly `403 Forbidden: bot was blocked by the user`; the exact text is **[unverified]** in the docs). Mark the channel as broken and show it on the website.

### Bot posts to one group
- Onboarding is simpler: invite people to a group. But nothing links a Telegram identity to a website member, every member sees every alert (noise), and the group cap of 20 messages per minute matters in bursts.
- This conflicts with the per-member Watch model. Use it only as an owner/admin channel, for example for "scraper unhealthy" alerts.

## Email

All of these need a **custom domain you control** with SPF/DKIM, and DMARC is recommended. Resend says "You must add and verify at least one domain to send emails with Resend" ([Resend domains](https://resend.com/docs/dashboard/domains/introduction)). Sending as `@gmail.com` through a third party fails DMARC alignment. A cheap domain (~£5–10/yr) is the one unavoidable cost of email **[price unverified]**. The same provider can send the magic-link emails.

| Provider | Free tier (primary source) | Notes |
|---|---|---|
| **Resend** | 3,000/month, **100/day**, 3 domains, 30-day retention ([pricing](https://resend.com/pricing)) | API limit "10 requests per second per team" ([API intro](https://resend.com/docs/api-reference/introduction)). Simple REST API. |
| **Brevo** | **300/day**, no card. Once the daily cap is hit, up to 1,000 transactional emails wait in a retry queue (via Brevo search snippets; the [help page](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan) returned 403 when fetched) **[partly unverified]** | Highest free daily cap. Whether Brevo adds its branding to free transactional mail is **[unverified]**. |
| **Mailgun** | **100/day**, 1 custom domain, 1-day log retention ([pricing](https://www.mailgun.com/pricing/)) | Short logs make delivery debugging hard. |
| **Amazon SES** | Not free long term: $0.10 per 1,000 (à la carte). New accounts get up to $200 in credits on a 6-month free plan ([pricing](https://aws.amazon.com/ses/pricing/)) | New accounts start in a sandbox (verified recipients only) until production access is approved **[sandbox details not on pricing page; unverified here]**. Costs pennies, but needs an AWS account and card. |

**Volume check:** 20 members × a burst of 1 grouped email each is 20 emails. Magic links add a few a day. Without grouping, a release drop matching 5 slots × 20 members is 100 emails, which would hit the Resend and Mailgun daily caps in one burst. So **group matches into one email per member per scan**. Brevo's 300/day gives the most headroom.

**Per-member onboarding:** none beyond the email used for sign-in. They should whitelist the sender.

**Deliverability gotchas:**
- New domains have no reputation, so alerts may land in spam at first.
- Gmail and Outlook push notifications for new mail can be slow or batched. Email is the slowest channel for near-real-time slots.

## Comparison

| | Telegram bot DM | Email (Resend/Brevo) | WhatsApp Cloud API | CallMeBot |
|---|---|---|---|---|
| Cost (5–20 members) | Free | Free tier + ~£5–10/yr domain | ~£5–30+/month, card required (rate unverified) | Free |
| Owner setup | Minutes (BotFather) | Domain + DNS, ~1 h | Meta app, number, template approval, billing: hours to days | None |
| Member onboarding | Tap deep link, press Start | Nothing (already signed in) | Phone number + opt-in | Message a bot, paste API key |
| Burst handling | 30 msg/s overall | Daily caps of 100–300, so group alerts | 250 recipients/day limit (fine) | Unknown |
| Reliability / risk | High, official, free | Good once the domain has reputation; spam risk early | High, but pricing and category risk; 1 Oct 2026 pricing change | Unofficial, "personal use only", no SLA |

**Takeaway:** Telegram (bot DM with deep-link linking) and email (Brevo or Resend, also sending magic links) meet the "free" constraint cleanly. WhatsApp fails "cheap and easy": the Cloud API costs money per alert, needs a separate number and template approval, and alerts may be classified as marketing. CallMeBot is free but is an unofficial, personal-use service. Leave WhatsApp out of v1, or at most offer CallMeBot as an explicitly "best effort" option.
