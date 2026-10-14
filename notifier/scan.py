"""The `scan` job: unless a release holds the night, read all three courts, record them in the snapshot, send the alerts and the 20:00 heads-up, and ping Healthchecks."""

import json
import os
import sys
import time

from notifier.health import ping, should_ping
from notifier.scraper import COURTS, REQUEST_GAP, scan_court
from notifier.supabase import rpc
from notifier.telegram import send_message


def main():
    if rpc("release_claim_held"):
        print("release in progress: scan skipped")
        return
    courts = []
    for i, (number, court) in enumerate(COURTS.items()):
        if i:
            time.sleep(REQUEST_GAP)
        result = scan_court(court)
        print(f"court {number}: {result['weeks']} weeks, {len(result['slots'])} slots {result.get('error', '')}".rstrip())
        courts.append({"court": number, **result})
    result = rpc("record_scan", courts=courts)
    print("record_scan:", json.dumps({k: v for k, v in result.items() if k != "messages"}))
    outcomes = send_and_report(result["messages"])
    outcomes += send_heads_up()
    # Pings go after the sends, so a revoked bot token (401) withholds them.
    if should_ping(result, outcomes):
        ping("scan")
    else:
        print("ping: withheld")
    if result.get("failed"):
        sys.exit("some courts could not be recorded")


def send_and_report(messages):
    """Send each message, then report the outcome for the alert rows it carries.

    Returns the HTTP status of each send.
    """
    outcomes = []
    for message in messages:
        status, error = send_message(message["chat_id"], message["text"])
        if status == 200:
            rpc("mark_sent", alert_ids=message["alert_ids"])
        else:
            rpc("mark_failed", alert_ids=message["alert_ids"], http_status=status, error=error)
        print(f"message for {len(message['alert_ids'])} slots: {status} {error or ''}".rstrip())
        outcomes.append(status)
    return outcomes


def send_heads_up():
    """Send this evening's heads-ups if they're due, then mark them done.

    Returns the HTTP status of each send.
    """
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{os.getpid()}"
    due = rpc("heads_up_due", run_id=run_id)
    if due is None:
        return []
    outcomes = []
    for message in due["messages"]:
        status, error = send_message(message["chat_id"], message["text"])
        print(f"heads-up: {status} {error or ''}".rstrip())
        outcomes.append(status)
    rpc("mark_heads_up_done", day=due["for_date"])
    return outcomes


if __name__ == "__main__":
    main()
