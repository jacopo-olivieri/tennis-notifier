# When to alert and how often to check

Type: grilling
Mode: HITL
Status: open
Blocked by: 01
Map: [Lincoln's Inn Fields court notifier](../map.md)

## Question

Given the observed release time and cancellation rate, what exactly triggers an alert, and what checking schedule catches it fast enough without hammering the site?

Sub-questions:
- Should release drops be detected by polling right after release, or should there also be a reminder before release ("Sat 18:00 opens at 00:00 tonight")?
- Is polling for cancellations worth it at all if they turn out to be very rare?
- How should alerts be grouped when one release matches many slots?
