from datetime import date, datetime

from tests.db.test_cancellation_alerts import OWNER, link, member, single, weekly
from tests.db.test_record_scan import court

RELEASING = date(2026, 11, 18)  # opens at midnight between 14 and 15 Oct


def claim(db, run_id, day=RELEASING):
    return db.call("claim_release", day, run_id)


def held(db, at):
    db.at(at)
    return db.one("select release_claim_held()")


def scan(db, at, free_by_court=None, days=42):
    """Scan at `at` with everything booked except `free_by_court`; returns the result."""
    db.at(at)
    courts = [court(n, free=(free_by_court or {}).get(n, ()), days=days) for n in (1, 2, 3)]
    return db.call("record_scan", courts)


def release(db, at, day=RELEASING):
    db.at(at)
    return db.call("record_release", day)


# --- the claim ------------------------------------------------------------

def test_only_the_first_run_holds_the_claim(db):
    db.at("2026-10-14 23:45")
    assert claim(db, "run-a") is True

    db.at("2026-10-14 23:50")
    assert claim(db, "run-b") is False
    assert claim(db, "run-a") is True


def test_a_claim_is_only_taken_from_23_30_to_00_15(db):
    db.at("2026-10-14 15:00")  # e.g. dispatched by hand: it mustn't stop the scans until midnight
    assert claim(db, "run-a") is False
    assert held(db, "2026-10-14 15:01") is False

    db.at("2026-10-15 00:15")  # too late: the scans have taken over
    assert claim(db, "run-b") is False

    db.at("2026-10-15 00:14")  # a late run still records the release
    assert claim(db, "run-c") is True

def test_no_claim_is_held_until_a_run_claims_the_night(db):
    assert held(db, "2026-10-14 23:44") is False

    claim(db, "run-a")

    assert held(db, "2026-10-14 23:46") is True


def test_the_claim_lapses_at_00_15_if_the_release_never_completes(db):
    db.at("2026-10-14 23:45")
    claim(db, "run-a")

    assert held(db, "2026-10-15 00:00:10") is True
    assert held(db, "2026-10-15 00:14:59") is True
    assert held(db, "2026-10-15 00:15") is False
    assert held(db, "2026-10-15 23:46") is False


# --- record_release -------------------------------------------------------

def test_the_release_alerts_every_watched_slot_free_on_the_new_day(db):
    owner = member(db)
    weekly(db, owner, 3, 10)  # Wednesdays 10:00
    single(db, owner, RELEASING, 12)
    weekly(db, owner, 3, 14)  # booked: not alerted
    weekly(db, owner, 3, 17)  # free, but on another Wednesday
    friend = member(db, 222, "Friend")
    weekly(db, friend, 4, 10)  # Thursdays: nothing on the new day
    scan(db, "2026-10-14 23:30", {
        1: {(RELEASING, 10), (RELEASING, 9)},
        2: {(RELEASING, 12), (date(2026, 11, 11), 17)},
        3: {(RELEASING, 10), (date(2026, 11, 19), 10)},
    })
    db.at("2026-10-14 23:45")
    claim(db, "run-a")

    [message] = release(db, "2026-10-14 23:59:55")

    assert message["chat_id"] == OWNER
    assert message["text"] == (
        "<b>🎾 Just released</b>\n\n"
        f"Wed 18 Nov 10:00  {link(1)} {link(3)}\n"
        f"Wed 18 Nov 12:00  {link(2)}"
    )
    assert db.rows("select member_id, court, date, hour, kind, created_at from alert order by id") == [
        (owner, c, RELEASING, h, "release", datetime(2026, 10, 14, 23, 59, 55)) for c, h in ((1, 10), (2, 12), (3, 10))
    ]
    assert sorted(message["alert_ids"]) == message["alert_ids"] == db.one("select array_agg(id order by id) from alert")


def test_recording_the_release_ends_the_claim(db):
    db.at("2026-10-14 23:45")
    claim(db, "run-a")

    assert release(db, "2026-10-15 00:00:05") == []

    assert held(db, "2026-10-15 00:00:06") is False
    assert db.one("select done_at from marker") == datetime(2026, 10, 15, 0, 0, 5)


def test_a_second_release_call_does_not_alert_twice(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 23:30", {1: {(RELEASING, 10)}})
    db.at("2026-10-14 23:45")
    claim(db, "run-a")
    [message] = release(db, "2026-10-15 00:00:05")

    assert release(db, "2026-10-15 00:00:20") == []
    db.one("select mark_sent(%s::bigint[])", [message["alert_ids"]])
    assert release(db, "2026-10-15 00:01") == []
    assert db.one("select count(*) from alert") == 1


# --- clock boundaries -----------------------------------------------------

def test_a_slot_entering_the_window_unchanged_is_alerted_by_the_release_not_the_scan(db):
    weekly(db, member(db), 3, 10)
    assert scan(db, "2026-10-14 23:30", {2: {(RELEASING, 10)}})["messages"] == []
    assert scan(db, "2026-10-14 23:59", {2: {(RELEASING, 10)}})["messages"] == []

    assert scan(db, "2026-10-15 00:00:10", {2: {(RELEASING, 10)}})["messages"] == []
    [message] = release(db, "2026-10-15 00:00:10")

    assert message["text"] == f"<b>🎾 Just released</b>\n\nWed 18 Nov 10:00  {link(2)}"


def test_the_release_on_the_night_the_clocks_go_back(db):
    sat_28_nov = date(2026, 11, 28)  # opens at midnight between 24 and 25 Oct, still BST
    weekly(db, member(db), 6, 9)
    scan(db, "2026-10-24 23:30", {3: {(sat_28_nov, 9)}}, days=49)
    db.at("2026-10-24 23:45")
    assert claim(db, "run-a", sat_28_nov) is True
    assert held(db, "2026-10-24 23:59:59") is True

    assert scan(db, "2026-10-25 00:00:10", {3: {(sat_28_nov, 9)}}, days=49)["messages"] == []
    assert held(db, "2026-10-25 00:00:10") is True
    [message] = release(db, "2026-10-25 00:00:10", sat_28_nov)

    assert message["text"] == f"<b>🎾 Just released</b>\n\nSat 28 Nov 09:00  {link(3)}"
    assert held(db, "2026-10-25 00:00:11") is False


def test_an_unfinished_claim_lapses_at_00_15_on_the_night_the_clocks_go_back(db):
    sat_28_nov = date(2026, 11, 28)
    db.at("2026-10-24 23:45")
    claim(db, "run-a", sat_28_nov)

    assert held(db, "2026-10-25 00:14:59") is True
    assert held(db, "2026-10-25 00:15") is False
    assert held(db, "2026-10-25 01:30") is False  # the hour that happens twice
