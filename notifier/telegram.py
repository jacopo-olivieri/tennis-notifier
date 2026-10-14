"""Sends the bot's DMs through the Telegram Bot API. Stdlib only."""

import json
import os
import urllib.error
import urllib.request


def send_message(chat_id, text):
    """Send one HTML message without link previews.

    Returns (http_status, error): (200, None) when sent; on failure the status is
    None if no response came back. The SQL side decides what a failure means.
    """
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        data=json.dumps({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        try:
            description = json.loads(e.read()).get("description")
        except ValueError:
            description = None
        return e.code, description or e.reason
    except OSError as e:  # URLError, timeouts: no response
        return None, f"{type(e).__name__}: {e}"
