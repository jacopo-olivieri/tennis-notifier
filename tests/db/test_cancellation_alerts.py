from datetime import date, datetime

from tests.db.test_record_scan import all_courts, court

WED_14_OCT = date(2026, 10, 14)
OWNER = 111
COURT_PAGE = {
    1: "https://camdenactive.camden.gov.uk/courses/detail/171/lincoln-s-inn-fields-tennis-court-1/",
    2: "https://camdenactive.camden.gov.uk/courses/detail/176/lincoln-s-inn-fields-tennis-court-2/",
    3: "https://camdenactive.camden.gov.uk/courses/detail/177/lincoln-s-inn-fields-tennis-court-3/",
}


def member(db, telegram_id=OWNER, name="Owner"):
    return db.one("insert into member (telegram_id, first_name) values (%s, %s) returning id", [telegram_id, name])


def weekly(db, member_id, weekday, hour):
    db.conn.execute("insert into watch (member_id, weekday, hour) values (%s, %s, %s)", [member_id, weekday, hour])


def single(db, member_id, day, hour):
    db.conn.execute("insert into watch (member_id, date, hour) values (%s, %s, %s)", [member_id, day, hour])


def link(n):
    return f'<a href="{COURT_PAGE[n]}">C{n}</a>'


def free_up(db, free_by_court, at="2026-10-14 09:05"):
    """Scan everything booked, then scan again at `at` with `free_by_court` slots free."""
    db.call("record_scan", all_courts())
    db.at(at)
    return db.call("record_scan", all_courts(**{f"c{n}": court(n, free=free) for n, free in free_by_court.items()}))


def alerts(db):
    return db.rows("select member_id, court, date, hour, kind, created_at, sent_at from alert order by id")


def test_a_watched_slot_freed_up_messages_its_member(db):
    owner = member(db)
    weekly(db, owner, 3, 10)  # Wednesdays 10:00

    result = free_up(db, {3: {(WED_14_OCT, 10)}})

    [message] = result["messages"]
    assert message["chat_id"] == OWNER
    assert message["text"] == f"<b>🎾 Court free</b>\n\nWed 14 Oct 10:00  {link(3)}"
    assert alerts(db) == [(owner, 3, WED_14_OCT, 10, "cancellation", datetime(2026, 10, 14, 9, 5), None)]
    assert message["alert_ids"] == db.one("select array_agg(id) from alert")


def test_a_single_date_watch_matches_only_its_date(db):
    owner = member(db)
    single(db, owner, date(2026, 10, 21), 10)

    result = free_up(db, {1: {(WED_14_OCT, 10), (date(2026, 10, 21), 10)}})

    [message] = result["messages"]
    assert message["text"] == f"<b>🎾 Court free</b>\n\nWed 21 Oct 10:00  {link(1)}"


def test_an_unwatched_slot_freed_up_sends_nothing(db):
    owner = member(db)
    weekly(db, owner, 3, 11)

    result = free_up(db, {2: {(WED_14_OCT, 10)}})

    assert result["messages"] == []
    assert alerts(db) == []


def test_booked_then_missing_then_free_is_a_cancellation(db):
    owner = member(db)
    slot = (date(2026, 10, 20), 10)
    weekly(db, owner, 2, 10)
    db.call("record_scan", all_courts())
    db.at("2026-10-14 09:05")
    assert db.call("record_scan", all_courts(c1=court(1, missing={slot})))["messages"] == []

    db.at("2026-10-14 09:10")
    result = db.call("record_scan", all_courts(c1=court(1, free={slot})))

    [message] = result["messages"]
    assert message["text"] == f"<b>🎾 Court free</b>\n\nTue 20 Oct 10:00  {link(1)}"
    assert alerts(db) == [(owner, 1, *slot, "cancellation", datetime(2026, 10, 14, 9, 10), None)]


def test_the_last_bookable_day_alerts_but_the_day_after_does_not(db):
    owner = member(db)
    last, after = date(2026, 11, 17), date(2026, 11, 18)  # window_end() is 17 Nov
    single(db, owner, last, 9)
    single(db, owner, after, 9)

    result = free_up(db, {2: {(last, 9), (after, 9)}})

    [message] = result["messages"]
    assert message["text"] == f"<b>🎾 Court free</b>\n\nTue 17 Nov 09:00  {link(2)}"
    assert [(d, h) for _, _, d, h, *_ in alerts(db)] == [(last, 9)]


def test_a_slot_that_has_started_is_not_alerted(db):
    owner = member(db)
    weekly(db, owner, 3, 9)
    weekly(db, owner, 3, 10)
    weekly(db, owner, 7, 10)  # Sunday 11 Oct is already past

    result = free_up(db, {1: {(WED_14_OCT, 9), (WED_14_OCT, 10), (date(2026, 10, 11), 10)}}, at="2026-10-14 09:59")

    [message] = result["messages"]
    assert message["text"] == f"<b>🎾 Court free</b>\n\nWed 14 Oct 10:00  {link(1)}"

    db.at("2026-10-14 10:00")
    assert db.call("record_scan", all_courts(c2=court(2, free={(WED_14_OCT, 10)})))["messages"] == []


def test_one_message_per_member_lists_hours_in_order_with_courts_ascending(db):
    owner = member(db)
    friend = member(db, 222, "Friend")
    for weekday in (3, 4):
        for hour in (9, 10, 17):
            weekly(db, owner, weekday, hour)
    weekly(db, friend, 4, 17)
    thu = date(2026, 10, 15)

    result = free_up(db, {
        1: {(thu, 17), (WED_14_OCT, 17)},
        2: {(WED_14_OCT, 10), (thu, 9)},
        3: {(thu, 17), (WED_14_OCT, 10)},
    })

    assert [m["chat_id"] for m in result["messages"]] == [OWNER, 222]
    owners, friends = result["messages"]
    assert owners["text"] == (
        "<b>🎾 Courts free</b>\n\n"
        f"Wed 14 Oct 10:00  {link(2)} {link(3)}\n"
        f"Wed 14 Oct 17:00  {link(1)}\n"
        f"Thu 15 Oct 09:00  {link(2)}\n"
        f"Thu 15 Oct 17:00  {link(1)} {link(3)}"
    )
    assert len(owners["alert_ids"]) == 6
    assert friends["text"] == f"<b>🎾 Courts free</b>\n\nThu 15 Oct 17:00  {link(1)} {link(3)}"
    assert db.one("select count(*) from alert") == 8


def test_a_member_watching_a_slot_both_weekly_and_by_date_is_alerted_once(db):
    owner = member(db)
    weekly(db, owner, 3, 10)
    single(db, owner, WED_14_OCT, 10)

    result = free_up(db, {3: {(WED_14_OCT, 10)}})

    [message] = result["messages"]
    assert message["text"] == f"<b>🎾 Court free</b>\n\nWed 14 Oct 10:00  {link(3)}"
    assert len(alerts(db)) == 1


def test_a_slot_seen_free_on_its_first_scan_or_going_free_to_booked_sends_nothing(db):
    owner = member(db)
    weekly(db, owner, 3, 10)
    slot = (WED_14_OCT, 10)

    assert db.call("record_scan", all_courts(c1=court(1, free={slot})))["messages"] == []
    db.at("2026-10-14 09:05")
    assert db.call("record_scan", all_courts())["messages"] == []
    assert alerts(db) == []


def test_a_skipped_court_sends_nothing(db):
    owner = member(db)
    weekly(db, owner, 3, 10)
    db.call("record_scan", all_courts())

    db.at("2026-10-14 09:05")
    result = db.call("record_scan", all_courts(c1=court(1, free={(WED_14_OCT, 10)}, weeks=5)))

    assert result["messages"] == []


def test_mark_sent_stamps_the_alerts_sent(db):
    owner = member(db)
    weekly(db, owner, 3, 10)
    [message] = free_up(db, {2: {(WED_14_OCT, 10)}, 3: {(WED_14_OCT, 10)}})["messages"]

    db.at("2026-10-14 09:06")
    db.one("select mark_sent(%s::bigint[])", [message["alert_ids"]])

    assert db.rows("select sent_at, failures, last_error from alert") == [(datetime(2026, 10, 14, 9, 6), 0, None)] * 2


def test_mark_failed_counts_the_failure_and_keeps_the_error(db):
    owner = member(db)
    weekly(db, owner, 3, 10)
    [message] = free_up(db, {3: {(WED_14_OCT, 10)}})["messages"]

    db.one("select mark_failed(%s::bigint[], 403, %s)", [message["alert_ids"], "Forbidden: bot was blocked by the user"])
    assert db.rows("select sent_at, failures, last_error from alert") == [
        (None, 1, "403 Forbidden: bot was blocked by the user"),
    ]

    db.one("select mark_failed(%s::bigint[], null, %s)", [message["alert_ids"], "timed out"])
    assert db.rows("select sent_at, failures, last_error from alert") == [(None, 2, "timed out")]
