"""The `scan` job: read all three courts and record them in the snapshot."""

import json
import sys
import time

from notifier.scraper import COURTS, REQUEST_GAP, scan_court
from notifier.supabase import rpc


def main():
    courts = []
    for i, (number, court) in enumerate(COURTS.items()):
        if i:
            time.sleep(REQUEST_GAP)
        result = scan_court(court)
        print(f"court {number}: {result['weeks']} weeks, {len(result['slots'])} slots {result.get('error', '')}".rstrip())
        courts.append({"court": number, **result})
    result = rpc("record_scan", courts=courts)
    print("record_scan:", json.dumps(result))
    if result.get("failed"):
        sys.exit("some courts could not be recorded")


if __name__ == "__main__":
    main()
