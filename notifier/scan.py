"""The `scan` job: read all three courts, record them in the snapshot and send the alerts."""

import json
import sys
import time

from notifier.scraper import COURTS, REQUEST_GAP, scan_court
from notifier.supabase import rpc
from notifier.telegram import send_message


def main():
    courts = []
    for i, (number, court) in enumerate(COURTS.items()):
        if i:
            time.sleep(REQUEST_GAP)
        result = scan_court(court)
        print(f"court {number}: {result['weeks']} weeks, {len(result['slots'])} slots {result.get('error', '')}".rstrip())
        courts.append({"court": number, **result})
    result = rpc("record_scan", courts=courts)
    print("record_scan:", json.dumps({k: v for k, v in result.items() if k != "messages"}))
    send_and_report(result["messages"])
    if result.get("failed"):
        sys.exit("some courts could not be recorded")


def send_and_report(messages):
    """Send each message, then report the outcome for the alert rows it carries."""
    for message in messages:
        status, error = send_message(message["chat_id"], message["text"])
        if status == 200:
            rpc("mark_sent", alert_ids=message["alert_ids"])
        else:
            rpc("mark_failed", alert_ids=message["alert_ids"], http_status=status, error=error)
        print(f"message for {len(message['alert_ids'])} slots: {status} {error or ''}".rstrip())


if __name__ == "__main__":
    main()
