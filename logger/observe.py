"""Temporary logger for the "Observe a week of releases and cancellations" ticket.

Every run probes the edge of the booking window (cheap), then scans the full
availability grid of every court and logs slot changes.
Stdlib only, so it runs anywhere without installs.
"""

import html
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = "https://camdenactive.camden.gov.uk"
LONDON = ZoneInfo("Europe/London")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
COURTS = {
    1: {"page": "/courses/detail/171/lincoln-s-inn-fields-tennis-court-1/", "event_id": 192},
    2: {"page": "/courses/detail/176/lincoln-s-inn-fields-tennis-court-2/", "event_id": 199},
    3: {"page": "/courses/detail/177/lincoln-s-inn-fields-tennis-court-3/", "event_id": 200},
}
PROBE_HOURS = range(7, 22)
PROBE_OFFSETS = (34, 35)  # days ahead of today (London): the current edge and the next one
SCAN_WEEKS = 6  # current week + 5 postbacks covers the 34-day window
SCAN_EVERY = timedelta(minutes=4)  # i.e. every run; short-lived cancellations need frequent scans
STOP_AFTER = date(2026, 10, 12)  # the observation week ends; scheduled runs become no-ops

DATA = Path(__file__).resolve().parent.parent / "data"
STATE = DATA / "state.json"
PROBES = DATA / "probes.jsonl"
EVENTS = DATA / "events.jsonl"
SCANS = DATA / "scans.jsonl"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def session(follow_redirects=True):
    jar = http.cookiejar.CookieJar()
    handlers = [urllib.request.HTTPCookieProcessor(jar)]
    if not follow_redirects:
        handlers.append(NoRedirect())
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [("User-Agent", UA), ("Accept-Language", "en-GB,en;q=0.9")]
    return opener


def fetch(opener, url, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    with opener.open(url, body, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def append(path, record):
    with path.open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


# --- probe: which (date, hour) pairs past the edge accept a booking attempt ---

def probe_slot(opener, event_id, day, hour):
    """'open' if book.aspx sends us to login, 'refused' if back to the detail page."""
    qs = urllib.parse.urlencode({"fdCourseEventId": event_id, "fdDate": day.strftime("%d/%m/%Y"), "fdTime": hour})
    try:
        opener.open(f"{BASE}/courses/book.aspx?{qs}", timeout=60)
        return "no-redirect"
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303):
            return f"http-{e.code}"
        return "open" if "login.aspx" in e.headers.get("Location", "") else "refused"


def probe(now):
    opener = session(follow_redirects=False)
    court = COURTS[1]
    fetch(opener, BASE + court["page"])  # book.aspx needs a site session cookie
    today = now.date()
    result = {}
    for offset in PROBE_OFFSETS:
        day = today + timedelta(days=offset)
        result[day.isoformat()] = {str(h): probe_slot(opener, court["event_id"], day, h) for h in PROBE_HOURS}
    record = {"at": now.isoformat(timespec="seconds"), "court": 1, "slots": result}
    append(PROBES, record)
    open_days = [d for d, hours in result.items() if "open" in hours.values()]
    print(f"probe: days with an open hour: {open_days}")


# --- scan: full grid for every court ---

DAY_RE = re.compile(r'<div class="timetable-day".*?<h4 class="timetable-title">\s*\w+ (\d{1,2})/(\d{1,2})</h4>(.*?)</ul>', re.S)
SLOT_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
HOUR_RE = re.compile(r'class="facility-hour">(\d{2}):00')
HIDDEN_RE = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
WEEK_START_RE = re.compile(r'name="ctl00\$PageContent\$fdWeekStart"[^>]*value="(\d{2})/(\d{2})/(\d{4})"')


def parse_week(page):
    m = WEEK_START_RE.search(page)
    if not m:
        raise ValueError("week start not found; page layout may have changed")
    week_start = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    slots = {}
    for dd, mm, body in DAY_RE.findall(page):
        day = week_start
        while (day.day, day.month) != (int(dd), int(mm)):
            day += timedelta(days=1)
            if day - week_start > timedelta(days=7):
                raise ValueError(f"day {dd}/{mm} not within week of {week_start}")
        for li in SLOT_RE.findall(body):
            hm = HOUR_RE.search(li)
            if not hm:
                continue
            if "facility-book" in li:
                status = "free"
            else:
                text = re.sub(r"<[^>]+>", " ", li)
                text = " ".join(html.unescape(text).split()[1:])
                status = text.lower() or "unknown"
            slots[f"{day.isoformat()}T{hm.group(1)}"] = status
    return week_start, slots


def scan_court(court):
    opener = session()
    url = BASE + court["page"]
    page = fetch(opener, url)
    slots = {}
    for week in range(SCAN_WEEKS):
        _, week_slots = parse_week(page)
        slots.update(week_slots)
        if week == SCAN_WEEKS - 1:
            break
        form = dict(HIDDEN_RE.findall(page))
        form = {k: html.unescape(v) for k, v in form.items()}
        form["__EVENTTARGET"] = "ctl00$PageContent$btnNextWeek"
        form["__EVENTARGUMENT"] = ""
        time.sleep(2)
        page = fetch(opener, url, form)
    return slots


def scan(now, state):
    started = time.monotonic()
    snapshot = {}
    for number, court in COURTS.items():
        for slot, status in scan_court(court).items():
            snapshot[f"{number}|{slot}"] = status
    previous = state.get("snapshot", {})
    at = now.isoformat(timespec="seconds")
    changes = 0
    for key in sorted(set(previous) | set(snapshot)):
        before, after = previous.get(key), snapshot.get(key)
        if before == after or not previous:
            continue
        court, slot = key.split("|")
        if after is None and slot < now.strftime("%Y-%m-%dT%H"):
            continue  # slot simply moved into the past
        append(EVENTS, {"at": at, "court": int(court), "slot": slot, "from": before, "to": after})
        changes += 1
    free = sum(1 for s in snapshot.values() if s == "free")
    append(SCANS, {"at": at, "slots": len(snapshot), "free": free, "changes": changes,
                   "seconds": round(time.monotonic() - started)})
    state["snapshot"] = snapshot
    state["last_scan"] = at
    print(f"scan: {len(snapshot)} slots, {free} free, {changes} changes")


def main():
    DATA.mkdir(exist_ok=True)
    now = datetime.now(LONDON)
    if now.date() > STOP_AFTER:
        print(f"observation ended on {STOP_AFTER}; nothing to do")
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    failed = False
    try:
        probe(now)
    except Exception as e:  # keep going so the scan still runs
        failed = True
        append(PROBES, {"at": now.isoformat(timespec="seconds"), "error": repr(e)})
        print(f"probe failed: {e!r}", file=sys.stderr)
    last = state.get("last_scan")
    if "--scan" in sys.argv or not last or now - datetime.fromisoformat(last) >= SCAN_EVERY:
        try:
            scan(now, state)
        except Exception as e:
            failed = True
            append(SCANS, {"at": now.isoformat(timespec="seconds"), "error": repr(e)})
            print(f"scan failed: {e!r}", file=sys.stderr)
    STATE.write_text(json.dumps(state, sort_keys=True, indent=0))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
