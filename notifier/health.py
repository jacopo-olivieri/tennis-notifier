"""The health signal: a Healthchecks.io dead-man's switch that alarms when pings stop. Stdlib only."""

import os
import urllib.request


def bot_token_ok(send_outcomes):
    """False if any send returned 401: the bot token was revoked.

    A member who blocked the bot gives 403, which isn't a health problem.
    """
    return 401 not in send_outcomes


def should_ping(scan_result, send_outcomes):
    """True only if record_scan succeeded, all 3 courts were complete and no send returned 401.

    scan_result is record_scan's result (None if it failed); send_outcomes are the
    HTTP statuses of this run's sends.
    """
    return scan_result is not None and scan_result["all_complete"] and bot_token_ok(send_outcomes)


def ping(check):
    """Ping a Healthchecks check, e.g. "scan", at the URL in HEALTHCHECKS_<CHECK>_URL.

    A failed ping is only printed: Healthchecks sees it as a missed ping.
    """
    url = os.environ.get(f"HEALTHCHECKS_{check.upper()}_URL")
    if not url:
        print(f"ping: no HEALTHCHECKS_{check.upper()}_URL, skipped")
        return
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            print(f"ping: {resp.status}")
    except OSError as e:
        print(f"ping failed: {type(e).__name__}: {e}")
