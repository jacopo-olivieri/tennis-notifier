"""The `release` job: claim tonight's release, wait for the new day to open at
midnight London time, then alert its watched free slots and ping Healthchecks.

Dispatched at 23:45 and 23:50; only the run holding the claim does anything,
and regular scans stand aside while it holds it.
"""

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from notifier.health import bot_token_ok, ping
from notifier.scan import send_and_report
from notifier.scraper import COURTS, REQUEST_GAP, SCAN_ERRORS, probe_session, slot_is_open
from notifier.supabase import rpc

LONDON = ZoneInfo("Europe/London")
WINDOW_DAYS = 34  # as in window_end(): the last bookable day is today + 34
PROBE_FROM = timedelta(seconds=-30)  # relative to midnight
PROBE_EVERY = 10  # seconds between probe rounds
# Over a week of logging, releases landed between 23:59:43 and 00:00:02. If the
# probe still hasn't seen the day open by 00:00:15, record the release anyway.
PROBE_UNTIL = timedelta(seconds=15)
PROBE_TIMEOUT = 5  # seconds per probe request, so a hanging site can't push past PROBE_UNTIL for long
PROBE_HOURS = (8, 11, 14)  # on court 1; any one taking a booking means the day is open


def releasing_day(now):
    """The day that opens at the coming midnight, or at the one just passed in a late run."""
    return now.date() + timedelta(days=WINDOW_DAYS + (1 if now.hour >= 12 else 0))


def release_midnight(day):
    return datetime.combine(day - timedelta(days=WINDOW_DAYS), datetime.min.time(), LONDON)


def sleep_until(moment):
    time.sleep(max(0, moment.timestamp() - time.time()))


def day_is_open(opener, day):
    for i, hour in enumerate(PROBE_HOURS):
        if i:
            time.sleep(REQUEST_GAP)
        if slot_is_open(opener, COURTS[1], day, hour, timeout=PROBE_TIMEOUT):
            return True
    return False


def wait_until_open(day):
    """Probe the day every PROBE_EVERY seconds from 23:59:30 until it opens or PROBE_UNTIL passes."""
    midnight = release_midnight(day)
    sleep_until(midnight + PROBE_FROM)
    opener = None
    while True:
        started = time.time()
        try:
            opener = opener or probe_session(timeout=PROBE_TIMEOUT)
            if day_is_open(opener, day):
                print(f"probe: {day} open at {datetime.now(LONDON):%H:%M:%S}")
                return
        except SCAN_ERRORS as e:  # e.g. a one-off 520: try again next round
            print(f"probe failed: {e!r}")
        if datetime.now(LONDON) >= midnight + PROBE_UNTIL:
            print(f"probe: {day} still not seen open at {datetime.now(LONDON):%H:%M:%S}, recording the release anyway")
            return
        time.sleep(max(0, PROBE_EVERY - (time.time() - started)))


def main():
    day = releasing_day(datetime.now(LONDON))
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{os.getpid()}"
    if not rpc("claim_release", day=day.isoformat(), run_id=run_id):
        print(f"release of {day}: not claimed (another run has it, or it isn't 23:30–00:15), exiting")
        return
    print(f"release of {day}: claimed by run {run_id}")
    wait_until_open(day)
    messages = rpc("record_release", day=day.isoformat())
    print(f"record_release: {len(messages)} messages")
    outcomes = send_and_report(messages)
    if not bot_token_ok(outcomes):
        print("ping: withheld")
        return
    # The release can land before midnight, but the check expects its ping after
    # 00:00: one sent earlier would count for the night before and raise a false alarm.
    sleep_until(release_midnight(day) + timedelta(seconds=1))
    ping("release")


if __name__ == "__main__":
    main()
