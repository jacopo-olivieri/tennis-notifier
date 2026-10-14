from datetime import date, datetime

from tests.db.test_cancellation_alerts import OWNER, member, single, weekly
from tests.db.test_release import RELEASING, scan

HEADS_UP = "<b>🌙 Opens at midnight</b>\n\n"


def heads_up(db, at, run_id="run-a"):
    db.at(at)
    return db.call("heads_up_due", run_id)


def reported(db, at, result):
    """Report the heads-ups' sends, as the scan job does once they're all sent."""
    db.at(at)
    db.call("mark_heads_up_done", date.fromisoformat(result["for_date"]))


def test_the_heads_up_lists_watched_hours_free_on_the_day_that_opens_at_midnight(db):
    owner = member(db)
    weekly(db, owner, 3, 10)  # Wednesdays 10:00
    single(db, owner, RELEASING, 12)
    single(db, owner, date(2026, 11, 25), 12)  # not yet open, and not tonight either
    weekly(db, owner, 3, 14)  # booked on every court: left out
    friend = member(db, 222, "Friend")
    weekly(db, friend, 4, 10)  # Thursdays: nothing opens tonight
    scan(db, "2026-10-14 19:55", {
        1: {(RELEASING, 10), (RELEASING, 9)},
        2: {(RELEASING, 12), (date(2026, 11, 25), 12), (date(2026, 11, 19), 10)},
        3: {(RELEASING, 10), (date(2026, 11, 11), 10)},
    })

    result = heads_up(db, "2026-10-14 20:00")

    assert result == {
        "for_date": "2026-10-14",
        "messages": [{
            "chat_id": OWNER,
            "text": HEADS_UP + "Wed 18 Nov 10:00  C1 C3\nWed 18 Nov 12:00  C2",
        }],
    }
    assert db.one("select count(*) from alert") == 0


def test_each_member_gets_their_own_heads_up(db):
    weekly(db, member(db), 3, 10)
    weekly(db, member(db, 222, "Friend"), 3, 11)
    scan(db, "2026-10-14 19:55", {2: {(RELEASING, 10), (RELEASING, 11)}})

    messages = heads_up(db, "2026-10-14 20:00")["messages"]

    assert messages == [
        {"chat_id": OWNER, "text": HEADS_UP + "Wed 18 Nov 10:00  C2"},
        {"chat_id": 222, "text": HEADS_UP + "Wed 18 Nov 11:00  C2"},
    ]


def test_nothing_before_20_00(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55", {1: {(RELEASING, 10)}})

    assert heads_up(db, "2026-10-14 19:59:59") is None
    assert db.one("select count(*) from marker") == 0

    assert heads_up(db, "2026-10-14 20:00")["messages"] != []


def test_only_one_heads_up_an_evening(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55", {1: {(RELEASING, 10)}})
    result = heads_up(db, "2026-10-14 20:00")
    reported(db, "2026-10-14 20:00:05", result)

    assert heads_up(db, "2026-10-14 20:05", "run-b") is None
    assert heads_up(db, "2026-10-14 23:55", "run-c") is None
    assert db.rows("select kind, for_date, claimed_by, claimed_at, done_at from marker") == [
        ("heads_up", date(2026, 10, 14), "run-a", datetime(2026, 10, 14, 20), datetime(2026, 10, 14, 20, 0, 5)),
    ]


def test_a_heads_up_whose_sends_were_never_reported_is_sent_by_the_next_scan(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55", {1: {(RELEASING, 10)}})
    first = heads_up(db, "2026-10-14 20:00")  # this run dies before reporting

    assert heads_up(db, "2026-10-14 20:05", "run-b") == first


def test_a_missed_20_00_run_is_caught_by_a_later_scan(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55", {1: {(RELEASING, 10)}})
    assert heads_up(db, "2026-10-14 19:55") is None

    [message] = heads_up(db, "2026-10-14 21:40")["messages"]

    assert message["text"] == HEADS_UP + "Wed 18 Nov 10:00  C1"


def test_an_evening_missed_entirely_is_not_sent_after_midnight(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55", {1: {(RELEASING, 10)}})

    assert heads_up(db, "2026-10-15 00:20") is None
    assert heads_up(db, "2026-10-15 19:59") is None


def test_an_evening_with_nothing_to_send_is_done_at_once(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55")  # all booked

    assert heads_up(db, "2026-10-14 20:00") == {"for_date": "2026-10-14", "messages": []}
    assert heads_up(db, "2026-10-14 20:05") is None
    assert db.one("select done_at from marker") == datetime(2026, 10, 14, 20)


def test_the_heads_up_follows_the_snapshot_at_the_time_it_is_sent(db):
    weekly(db, member(db), 3, 10)
    scan(db, "2026-10-14 19:55", {1: {(RELEASING, 10)}})
    scan(db, "2026-10-14 20:00")  # booked again before the heads-up

    assert heads_up(db, "2026-10-14 20:00")["messages"] == []


def test_the_heads_up_on_the_day_the_clocks_go_back(db):
    sun_29_nov = date(2026, 11, 29)  # opens at midnight between 25 and 26 Oct, the first GMT night
    weekly(db, member(db), 7, 9)
    scan(db, "2026-10-25 19:00", {3: {(date(2026, 11, 22), 9), (sun_29_nov, 9)}}, days=50)

    assert heads_up(db, "2026-10-25 19:59:59") is None
    [message] = heads_up(db, "2026-10-25 20:00")["messages"]

    assert message["text"] == HEADS_UP + "Sun 29 Nov 09:00  C3"
