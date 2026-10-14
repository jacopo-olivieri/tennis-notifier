"""Reads Lincoln's Inn Fields court availability from Camden Active.

Ported from logger/observe.py. Stdlib only, so the poller runs without installs.
"""

import html
import http.client
import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "https://camdenactive.camden.gov.uk"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
COURTS = {
    1: {"page": "/courses/detail/171/lincoln-s-inn-fields-tennis-court-1/", "event_id": 192},
    2: {"page": "/courses/detail/176/lincoln-s-inn-fields-tennis-court-2/", "event_id": 199},
    3: {"page": "/courses/detail/177/lincoln-s-inn-fields-tennis-court-3/", "event_id": 200},
}
SCAN_WEEKS = 6  # current week + 5 postbacks covers the 34-day window
REQUEST_GAP = 2  # seconds between any two requests, to be polite


class ParseError(ValueError):
    """The page doesn't look like a court timetable; its layout may have changed."""


# What a court's scan may fail on and still be logged as a failed court. Anything
# else is a bug in this code and should fail the job. URLError is an OSError.
SCAN_ERRORS = (OSError, http.client.HTTPException, ParseError)


DAY_RE = re.compile(r'<div class="timetable-day".*?<h4 class="timetable-title">\s*\w+ (\d{1,2})/(\d{1,2})</h4>(.*?)</ul>', re.S)
SLOT_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
HOUR_RE = re.compile(r'class="facility-hour">(\d{2}):00')
HIDDEN_RE = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
WEEK_START_RE = re.compile(r'name="ctl00\$PageContent\$fdWeekStart"[^>]*value="(\d{2})/(\d{2})/(\d{4})"')


def parse_week(page):
    """Return the week start and {(date, hour): "free" | "booked"} for one timetable page."""
    m = WEEK_START_RE.search(page)
    if not m:
        raise ParseError("week start not found")
    try:
        week_start = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError as e:
        raise ParseError(f"bad week start {m.group(0)!r}") from e
    days = DAY_RE.findall(page)
    if not days:
        raise ParseError(f"no days found in week of {week_start}")
    slots = {}
    for dd, mm, body in days:
        day = week_start
        while (day.day, day.month) != (int(dd), int(mm)):
            day += timedelta(days=1)
            if day - week_start >= timedelta(days=7):
                raise ParseError(f"day {dd}/{mm} not within week of {week_start}")
        for li in SLOT_RE.findall(body):
            hm = HOUR_RE.search(li)
            if hm:
                slots[(day, int(hm.group(1)))] = "free" if "facility-book" in li else "booked"
    return week_start, slots


def next_week_form(page):
    """Return the postback form that asks for the week after this page's."""
    form = {name: html.unescape(value) for name, value in HIDDEN_RE.findall(page)}
    form["__EVENTTARGET"] = "ctl00$PageContent$btnNextWeek"
    form["__EVENTARGUMENT"] = ""
    return form


def session(*handlers):
    """A cookie-keeping opener with a browser User-Agent."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), *handlers)
    opener.addheaders = [("User-Agent", UA), ("Accept-Language", "en-GB,en;q=0.9")]
    return opener


def fetch(opener, url, data=None, timeout=60):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    with opener.open(url, body, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def scan_court(court):
    """Read a court's 6-week grid: {"weeks": parsed, "slots": [...]}, plus "error" if it stopped early.

    Whether the court counts as complete is record_scan's call, not ours.
    """
    opener = session()
    url = BASE + court["page"]
    slots, weeks = {}, 0
    try:
        page = fetch(opener, url)
        while True:
            slots.update(parse_week(page)[1])
            weeks += 1
            if weeks == SCAN_WEEKS:
                break
            time.sleep(REQUEST_GAP)
            page = fetch(opener, url, next_week_form(page))
        error = None
    except SCAN_ERRORS as e:
        error = repr(e)
    result = {
        "weeks": weeks,
        "slots": [{"date": d.isoformat(), "hour": h, "status": s} for (d, h), s in sorted(slots.items())],
    }
    if error:
        result["error"] = error
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe_session(timeout=60):
    """A session that doesn't follow redirects, holding the site cookie book.aspx needs."""
    opener = session(_NoRedirect())
    fetch(opener, BASE + COURTS[1]["page"], timeout=timeout)
    return opener


def slot_is_open(opener, court, day, hour, timeout=60):
    """Whether book.aspx takes this slot: it redirects to login.aspx if the slot is
    open and free, and back to the court's page if it is booked or not open yet.

    The grid can't tell: it shows "Book" beyond the booking window too.
    """
    query = urllib.parse.urlencode({"fdCourseEventId": court["event_id"], "fdDate": day.strftime("%d/%m/%Y"), "fdTime": hour})
    try:
        opener.open(f"{BASE}/courses/book.aspx?{query}", timeout=timeout).close()
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303):
            raise
        return "login.aspx" in e.headers.get("Location", "")
    return False
