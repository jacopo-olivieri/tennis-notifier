"""Calls the shared SQL functions through Supabase's REST RPC endpoint. Stdlib only."""

import json
import os
import urllib.request


def rpc(function, **params):
    """POST to /rest/v1/rpc/<function> with the service key and return the decoded result."""
    key = os.environ["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("ey"):  # a legacy JWT key also goes in Authorization; new sb_secret_ keys must not
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        f"{os.environ['SUPABASE_URL'].rstrip('/')}/rest/v1/rpc/{function}",
        data=json.dumps(params).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as resp:
        return json.loads(resp.read())
