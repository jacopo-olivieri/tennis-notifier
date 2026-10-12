# Prototype the watch-management website

Type: prototype
Mode: HITL
Status: open
Blocked by:
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

What does the minimal website look like and how does it behave? Cover signing in, adding and removing recurring and one-off watches, choosing a channel, and (for the owner) inviting members. Build a rough clickable mock to react to. No backend.

## Comments

- 2026-10-12: From [Choose the hosting architecture](06-hosting-architecture.md), the site is static on GitHub Pages and talks to one Edge Function API. Signing in with the Telegram widget (`request_access=write`) is also how the channel gets connected, so there's no separate "choose a channel" or `/start` step. Saving a watch triggers the new-watch alert at once.
