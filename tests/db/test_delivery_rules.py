from datetime import date, datetime

from tests.db.test_cancellation_alerts import OWNER, WED_14_OCT, free_up, link, member, weekly
from tests.db.test_record_scan import all_courts, court

WED_17 = (WED_14_OCT, 17)
BLOCKED = (403, "Forbidden: bot was blocked by the user")


def sent(db, message):
    db.one("select mark_sent(%s::bigint[])", [message["alert_ids"]])


def failed(db, message, status=500, error="Internal Server Error"):
    db.one("select mark_failed(%s::bigint[], %s, %s)", [message["alert_ids"], status, error])


def scan(db, at, free_by_court=None):
    """Scan at `at` with everything booked except `free_by_court`; returns the messages."""
    db.at(at)
    courts = all_courts(**{f"c{n}": court(n, free=free) for n, free in (free_by_court or {}).items()})
    return db.call("record_scan", courts)["messages"]


def unreachable_since(db, member_id):
    return db.one("select unreachable_since from member where id = %s", [member_id])


def owner_watching_wed_17(db):
    owner = member(db)
    weekly(db, owner, 3, 17)
    return owner


# --- the 30-minute rule ---------------------------------------------------

def test_a_slot_flipping_back_free_within_30_minutes_is_not_alerted_again(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    sent(db, message)
    assert scan(db, "2026-10-14 09:10") == []

    assert scan(db, "2026-10-14 09:34", {2: {WED_17}}) == []
    assert db.one("select count(*) from alert") == 1


def test_the_rule_is_per_slot_and_per_member(db):
    owner = owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    sent(db, message)
    scan(db, "2026-10-14 09:10")
    friend = member(db, 222, "Friend")
    weekly(db, friend, 3, 17)

    messages = scan(db, "2026-10-14 09:15", {2: {WED_17}, 3: {WED_17}})

    assert [(m["chat_id"], m["text"]) for m in messages] == [
        (OWNER, f"<b>🎾 Court free</b>\n\nWed 14 Oct 17:00  {link(3)}"),
        (222, f"<b>🎾 Courts free</b>\n\nWed 14 Oct 17:00  {link(2)} {link(3)}"),
    ]
    assert db.rows("select member_id, court from alert where created_at = '2026-10-14 09:15' order by member_id, court") == [
        (owner, 3), (friend, 2), (friend, 3),
    ]


def test_a_slot_freed_again_more_than_30_minutes_after_the_send_is_alerted_again(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    sent(db, message)
    scan(db, "2026-10-14 09:20")
    assert scan(db, "2026-10-14 09:35", {2: {WED_17}}) == []
    scan(db, "2026-10-14 09:40")

    [again] = scan(db, "2026-10-14 09:45", {2: {WED_17}})

    assert again["text"] == f"<b>🎾 Court free</b>\n\nWed 14 Oct 17:00  {link(2)}"
    assert db.one("select count(*) from alert") == 2


def test_sending_an_alert_twice_keeps_its_first_sent_time(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    sent(db, message)
    db.at("2026-10-14 09:30")
    sent(db, message)
    scan(db, "2026-10-14 09:32")

    assert len(scan(db, "2026-10-14 09:36", {2: {WED_17}})) == 1


def test_an_abandoned_alert_does_not_count_toward_the_rule(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    for _ in range(3):
        failed(db, message)
    scan(db, "2026-10-14 09:10")

    [again] = scan(db, "2026-10-14 09:15", {2: {WED_17}})

    assert again["text"] == f"<b>🎾 Court free</b>\n\nWed 14 Oct 17:00  {link(2)}"
    assert again["alert_ids"] != message["alert_ids"]


# --- retries --------------------------------------------------------------

def test_a_failed_alert_is_retried_while_its_slot_is_still_free(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)

    [retry] = scan(db, "2026-10-14 09:10", {2: {WED_17}})

    assert retry == message
    assert db.one("select count(*) from alert") == 1
    db.at("2026-10-14 09:11")
    sent(db, retry)
    assert scan(db, "2026-10-14 09:15", {2: {WED_17}}) == []
    assert db.rows("select sent_at, failures from alert") == [(datetime(2026, 10, 14, 9, 11), 1)]


def test_a_failed_alert_is_not_retried_once_its_slot_is_booked_again(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)

    assert scan(db, "2026-10-14 09:10") == []


def test_a_freed_slot_with_an_alert_still_pending_is_sent_once_as_the_retry(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)
    scan(db, "2026-10-14 09:10")

    [retry] = scan(db, "2026-10-14 09:15", {2: {WED_17}})

    assert retry == message
    assert db.one("select count(*) from alert") == 1


def test_a_failed_alert_is_abandoned_after_3_failures(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)
    for at in ("2026-10-14 09:10", "2026-10-14 09:15"):
        [retry] = scan(db, at, {2: {WED_17}})
        failed(db, retry)

    assert scan(db, "2026-10-14 09:20", {2: {WED_17}}) == []
    assert db.rows("select sent_at, failures from alert") == [(None, 3)]


def test_a_failed_alert_is_not_retried_once_its_slot_has_started(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)

    assert scan(db, "2026-10-14 17:00", {2: {WED_17}}) == []


def test_an_alert_never_reported_is_left_to_its_sender_briefly_then_retried(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]  # the sender died before mark_sent

    assert scan(db, "2026-10-14 09:06", {2: {WED_17}}) == []
    assert scan(db, "2026-10-14 09:10", {2: {WED_17}}) == [message]


def test_a_court_that_failed_this_scan_does_not_drive_retries(db):
    owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)

    db.at("2026-10-14 09:10")
    result = db.call("record_scan", all_courts(c2=court(2, weeks=5)))

    assert result["messages"] == []


def test_a_retry_joins_new_cancellations_in_one_message(db):
    owner = owner_watching_wed_17(db)
    weekly(db, owner, 4, 9)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message)

    [combined] = scan(db, "2026-10-14 09:10", {2: {WED_17}, 1: {(date(2026, 10, 15), 9)}})

    assert combined["text"] == (
        "<b>🎾 Courts free</b>\n\n"
        f"Wed 14 Oct 17:00  {link(2)}\n"
        f"Thu 15 Oct 09:00  {link(1)}"
    )
    assert len(combined["alert_ids"]) == 2 and message["alert_ids"][0] in combined["alert_ids"]


def test_a_cancellation_with_a_retried_release_alert_is_headed_free_now(db):
    owner = owner_watching_wed_17(db)
    weekly(db, owner, 4, 9)
    thu = (date(2026, 10, 15), 9)
    db.call("record_scan", all_courts(c1=court(1, free={thu})))
    db.conn.execute(
        "insert into alert (member_id, court, date, hour, kind, failures) values (%s, 1, %s, %s, 'release', 1)",
        [owner, *thu],
    )

    [combined] = scan(db, "2026-10-14 09:05", {1: {thu}, 3: {WED_17}})

    assert combined["text"] == (
        "<b>🎾 Free now</b>\n\n"
        f"Wed 14 Oct 17:00  {link(3)}\n"
        f"Thu 15 Oct 09:00  {link(1)}"
    )


# --- unreachable members --------------------------------------------------

def test_a_member_whose_alert_is_abandoned_with_a_403_is_unreachable_until_a_send_succeeds(db):
    owner = owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    db.at("2026-10-14 09:06")
    failed(db, message, *BLOCKED)
    failed(db, message, *BLOCKED)
    assert unreachable_since(db, owner) is None

    db.at("2026-10-14 09:07")
    failed(db, message, *BLOCKED)
    assert unreachable_since(db, owner) == datetime(2026, 10, 14, 9, 7)

    [later] = scan(db, "2026-10-14 10:00", {3: {WED_17}})
    sent(db, later)
    assert unreachable_since(db, owner) is None


def test_an_alert_abandoned_with_another_status_leaves_the_member_reachable(db):
    owner = owner_watching_wed_17(db)
    [message] = free_up(db, {2: {WED_17}})["messages"]
    failed(db, message, *BLOCKED)
    failed(db, message, *BLOCKED)
    failed(db, message, None, "timed out")

    assert unreachable_since(db, owner) is None


def test_a_further_403_keeps_the_first_unreachable_time(db):
    owner = owner_watching_wed_17(db)
    [first] = free_up(db, {2: {WED_17}})["messages"]
    for _ in range(3):
        failed(db, first, *BLOCKED)

    [second] = scan(db, "2026-10-14 10:00", {3: {WED_17}})
    for _ in range(3):
        failed(db, second, *BLOCKED)

    assert unreachable_since(db, owner) == datetime(2026, 10, 14, 9, 5)
