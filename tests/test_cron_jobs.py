from scripts.cron_jobs import job_specs, plan

PAT = "github_pat_test"
DISPATCHES = "https://api.github.com/repos/jacopo-olivieri/tennis-notifier/actions/workflows/{}/dispatches"


def runs(workflow):
    """(hour, minute) of every run a day dispatching `workflow`."""
    times = set()
    for job in job_specs(PAT):
        if job["url"] == DISPATCHES.format(workflow):
            s = job["schedule"]
            times |= {(h, m) for h in s["hours"] for m in s["minutes"]}
    return times


def test_scan_runs_every_5_minutes_by_day_and_every_15_overnight():
    day = {(h, m) for h in range(7, 23) for m in range(0, 60, 5)}
    night = {(h, m) for h in [23, *range(7)] for m in range(0, 60, 15)}
    assert runs("scan.yml") == day | night


def test_release_runs_at_23_45_and_23_50():
    assert runs("release.yml") == {(23, 45), (23, 50)}


def test_every_job_runs_daily_in_london_time():
    for job in job_specs(PAT):
        s = job["schedule"]
        assert s["timezone"] == "Europe/London"
        assert s["mdays"] == s["months"] == s["wdays"] == [-1]
        assert s["expiresAt"] == 0


def test_every_job_posts_a_dispatch_of_main_with_the_pat():
    for job in job_specs(PAT):
        assert job["enabled"] is True
        assert job["requestMethod"] == 1  # POST
        assert job["extendedData"]["body"] == '{"ref":"main"}'
        assert job["extendedData"]["headers"]["Authorization"] == f"Bearer {PAT}"


def test_titles_are_distinct():
    titles = [job["title"] for job in job_specs(PAT)]
    assert len(set(titles)) == len(titles) == 3


def test_plan_creates_jobs_that_dont_exist_yet():
    specs = job_specs(PAT)
    assert plan([], specs) == [("create", None, spec) for spec in specs]


def test_plan_updates_jobs_matched_by_title_and_ignores_others():
    specs = job_specs(PAT)
    existing = [
        {"jobId": 7, "title": specs[0]["title"]},
        {"jobId": 9, "title": "someone else's job"},
    ]
    assert plan(existing, specs) == [
        ("update", 7, specs[0]),
        *[("create", None, spec) for spec in specs[1:]],
    ]
