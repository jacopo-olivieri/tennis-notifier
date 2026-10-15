"""The cron-job.org jobs that dispatch `scan` and `release`. Stdlib only.

    CRONJOB_API_KEY=... DISPATCH_PAT=... python3 scripts/cron_jobs.py

creates the jobs, or updates the ones already there (matched by title), so a
re-run with a new PAT is how the PAT is rotated. `scripts/go_live.sh` runs it.
"""

import json
import os
import sys
import time
import urllib.request

API = "https://api.cron-job.org"
DISPATCHES = "https://api.github.com/repos/jacopo-olivieri/tennis-notifier/actions/workflows/{}/dispatches"
POST = 1


def _job(title, workflow, hours, minutes, pat):
    return {
        "title": title,
        "url": DISPATCHES.format(workflow),
        "enabled": True,
        "requestMethod": POST,
        "requestTimeout": 30,
        "schedule": {
            "timezone": "Europe/London",
            "expiresAt": 0,
            "hours": hours,
            "minutes": minutes,
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1],
        },
        "extendedData": {
            "headers": {
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            "body": '{"ref":"main"}',
        },
    }


def job_specs(pat):
    """The three jobs: scans every 5 min 07:00–23:00 and every 15 min overnight, and the release at 23:45 and 23:50."""
    return [
        _job("tennis-notifier scan (day)", "scan.yml", list(range(7, 23)), list(range(0, 60, 5)), pat),
        _job("tennis-notifier scan (night)", "scan.yml", [23, *range(7)], [0, 15, 30, 45], pat),
        _job("tennis-notifier release", "release.yml", [23], [45, 50], pat),
    ]


def plan(existing, specs):
    """("update", jobId, spec) for a spec whose title already has a job, else ("create", None, spec)."""
    ids = {job["title"]: job["jobId"] for job in existing}
    return [("update", ids[s["title"]], s) if s["title"] in ids else ("create", None, s) for s in specs]


def _call(method, path, api_key, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read() or b"{}")


def main():
    api_key, pat = os.environ["CRONJOB_API_KEY"], os.environ["DISPATCH_PAT"]
    existing = _call("GET", "/jobs", api_key)["jobs"]
    for action, job_id, spec in plan(existing, job_specs(pat)):
        if action == "create":
            job_id = _call("PUT", "/jobs", api_key, {"job": spec})["jobId"]
        else:
            _call("PATCH", f"/jobs/{job_id}", api_key, {"job": spec})
        print(f"{action}d job {job_id}: {spec['title']}")
        time.sleep(1.5)  # creating is limited to 1 a second


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        sys.exit(f"cron-job.org: {type(e).__name__}: {e}")
