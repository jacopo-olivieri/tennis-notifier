# 07: 20:00 heads-up

**What to build:** at about 20:00 London time, each Member with watched hours on the day that opens at midnight gets one `🌙 Opens at midnight` message listing those hours and the courts free on the grid now, with no links. Spec: `heads_up_due`, Rules (heads-up marker), Message format.

**Blocked by:** 03

**Status:** ready-for-agent

- [ ] `heads_up_due()` returns nothing before 20:00; at or after 20:00 it claims the `heads_up` marker for today and returns Heads-ups for watched hours on today + 35 where at least one court shows free
- [ ] It returns nothing once the marker is done; the marker is set done only after its sends are reported
- [ ] Heads-up lines have no links; weekly and single-date watches (including dates not yet open) both qualify
- [ ] The `scan` job calls it on every run after the alerts
- [ ] SQL tests: 19:59 versus 20:00, only once per evening, a missed 20:00 run caught by a later scan, the BST→GMT day
