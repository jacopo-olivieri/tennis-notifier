import urllib.error
from datetime import date
from pathlib import Path

import pytest

from notifier import scraper
from notifier.scraper import COURTS, ParseError, next_week_form, parse_week, scan_court

SAMPLES = Path(__file__).resolve().parent.parent / "docs" / "research"


def sample(name):
    return (SAMPLES / name).read_text()


def test_parse_week_reads_free_and_booked_slots():
    week_start, slots = parse_week(sample("sample_week1_court1.html"))

    assert week_start == date(2026, 10, 11)
    assert len(slots) == 70
    free = sorted(k for k, status in slots.items() if status == "free")
    assert free == [
        (date(2026, 10, 12), 10),
        (date(2026, 10, 13), 10),
        (date(2026, 10, 13), 14),
        (date(2026, 10, 13), 15),
        (date(2026, 10, 14), 11),
        (date(2026, 10, 15), 11),
        (date(2026, 10, 15), 14),
        (date(2026, 10, 15), 15),
        (date(2026, 10, 16), 11),
    ]
    assert slots[(date(2026, 10, 11), 8)] == "booked"
    assert set(slots.values()) == {"free", "booked"}


@pytest.mark.parametrize(
    "break_page",
    [
        pytest.param(lambda p: p.replace("fdWeekStart", "fdSomethingElse"), id="no week start"),
        pytest.param(lambda p: p.replace("timetable-day", "timetable-row"), id="no day structure"),
    ],
)
def test_parse_week_raises_on_a_changed_layout(break_page):
    page = break_page(sample("sample_week1_court1.html"))

    with pytest.raises(ParseError):
        parse_week(page)


def test_next_week_form_carries_every_hidden_input_and_the_next_week_target():
    form = next_week_form(sample("sample_week0_court1.html"))

    assert form["__EVENTTARGET"] == "ctl00$PageContent$btnNextWeek"
    assert form["__EVENTARGUMENT"] == ""
    assert form["ctl00$PageContent$fdWeekStart"] == "04/10/2026"
    assert set(form) == {
        "ctl00_RadScriptManager1_TSM",
        "__EVENTTARGET",
        "__EVENTARGUMENT",
        "__AT",
        "__VIEWSTATE",
        "__VIEWSTATEGENERATOR",
        "__SCROLLPOSITIONX",
        "__SCROLLPOSITIONY",
        "__EVENTVALIDATION",
        "ctl00$PageContent$fdWeekStart",
        "ctl00$PageContent$fdFacilityId",
    }
    assert form["__VIEWSTATE"]
    assert "&#" not in form["__VIEWSTATE"]


def test_scan_court_records_a_network_failure_as_the_court_error(monkeypatch):
    def fetch(opener, url, data=None):
        raise urllib.error.HTTPError(url, 520, "Origin Error", {}, None)
    monkeypatch.setattr(scraper, "fetch", fetch)

    result = scan_court(COURTS[1])

    assert result["weeks"] == 0
    assert "520" in result["error"]


def test_scan_court_lets_a_code_bug_fail_the_job(monkeypatch):
    monkeypatch.setattr(scraper, "fetch", lambda opener, url, data=None: sample("sample_week1_court1.html"))
    def parse_week(page):
        raise TypeError("a bug")
    monkeypatch.setattr(scraper, "parse_week", parse_week)

    with pytest.raises(TypeError):
        scan_court(COURTS[1])
