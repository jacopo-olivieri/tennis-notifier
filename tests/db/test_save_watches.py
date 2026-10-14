from datetime import date

from tests.db.test_cancellation_alerts import OWNER, link, member, single, weekly
from tests.db.test_delivery_rules import failed, scan, sent
from tests.db.test_record_scan import all_courts, court

NEW_WATCHES = "<b>🎾 Free now for your new watches</b>\n"
TUE_20_OCT = date(2026, 10, 20)
TUE_27_OCT = date(2026, 10, 27)
FRI_23_OCT = date(2026, 10, 23)


def wk(weekday, hour):
    return {"weekday": weekday, "hour": hour}


def on(day, hour):
    return {"date": day.isoformat(), "hour": hour}


def save(db, member_id, added=(), removed=()):
    return db.call("save_watches", member_id, list(added), list(removed))


def watches(db, member_id):
    return db.rows("select weekday, date, hour from watch where member_id = %s order by weekday, date, hour", [member_id])


def snapshot(db, free_by_court):
    db.call("record_scan", all_courts(**{f"c{n}": court(n, free=free) for n, free in free_by_court.items()}))


# --- applying the batch ---------------------------------------------------

def test_a_save_adds_and_removes_watched_hours(db):
    owner = member(db)
    weekly(db, owner, 1, 18)
    weekly(db, owner, 6, 9)

    save(db, owner, added=[wk(2, 11), on(FRI_23_OCT, 15)], removed=[wk(1, 18)])

    assert watches(db, owner) == [(2, None, 11), (6, None, 9), (None, FRI_23_OCT, 15)]


def test_adding_an_hour_already_watched_keeps_one_row(db):
    owner = member(db)
    weekly(db, owner, 2, 11)

    save(db, owner, added=[wk(2, 11), wk(2, 11), on(FRI_23_OCT, 15), on(FRI_23_OCT, 15)])

    assert watches(db, owner) == [(2, None, 11), (None, FRI_23_OCT, 15)]


def test_a_single_date_may_be_after_the_booking_window(db):
    owner = member(db)

    save(db, owner, added=[on(date(2026, 12, 25), 10)])

    assert watches(db, owner) == [(None, date(2026, 12, 25), 10)]


def test_a_single_date_already_past_is_not_added(db):
    owner = member(db)

    save(db, owner, added=[on(date(2026, 10, 13), 10)])

    assert watches(db, owner) == []


def test_an_hour_already_started_today_is_not_added(db):
    owner = member(db)
    db.at("2026-10-14 10:30")

    save(db, owner, added=[on(date(2026, 10, 14), 10), on(date(2026, 10, 14), 11)])

    assert watches(db, owner) == [(None, date(2026, 10, 14), 11)]


def test_an_hour_removed_and_added_back_in_one_save_stays_watched_without_a_message(db):
    owner = member(db)
    weekly(db, owner, 2, 11)
    snapshot(db, {1: {(TUE_20_OCT, 11)}})

    assert save(db, owner, added=[wk(2, 11)], removed=[wk(2, 11)]) is None
    assert watches(db, owner) == [(2, None, 11)]


def test_a_save_touches_only_its_members_watches(db):
    owner = member(db)
    friend = member(db, 222, "Friend")
    weekly(db, friend, 2, 11)

    save(db, owner, added=[wk(3, 10)], removed=[wk(2, 11)])

    assert watches(db, friend) == [(2, None, 11)]
    assert watches(db, owner) == [(3, None, 10)]


def test_removing_an_hour_not_watched_does_nothing(db):
    owner = member(db)

    assert save(db, owner, removed=[wk(2, 11), on(FRI_23_OCT, 15)]) is None
    assert watches(db, owner) == []


# --- the new-watch message ------------------------------------------------

def test_the_message_lists_the_added_hours_then_the_slots_free_on_them(db):
    owner = member(db)
    snapshot(db, {1: {(TUE_20_OCT, 11)}, 2: {(TUE_27_OCT, 11)}, 3: {(TUE_27_OCT, 11), (FRI_23_OCT, 15)}})

    message = save(db, owner, added=[on(FRI_23_OCT, 15), wk(2, 11)])

    assert message["chat_id"] == OWNER
    assert message["text"] == (
        NEW_WATCHES + "Weekly Tue 11:00 · Fri 23 Oct 15:00\n\n"
        f"Tue 20 Oct 11:00  {link(1)}\n"
        f"Fri 23 Oct 15:00  {link(3)}\n"
        f"Tue 27 Oct 11:00  {link(2)} {link(3)}"
    )
    assert db.rows("select member_id, court, date, hour, kind, sent_at from alert order by id") == [
        (owner, 1, TUE_20_OCT, 11, "new_watch", None),
        (owner, 3, FRI_23_OCT, 15, "new_watch", None),
        (owner, 2, TUE_27_OCT, 11, "new_watch", None),
        (owner, 3, TUE_27_OCT, 11, "new_watch", None),
    ]
    assert message["alert_ids"] == db.one("select array_agg(id order by id) from alert")


def test_the_added_hours_line_lists_weekly_hours_first_then_single_dates_in_order(db):
    owner = member(db)
    snapshot(db, {1: {(TUE_20_OCT, 11)}})

    message = save(db, owner, added=[
        on(date(2026, 12, 25), 10), wk(7, 9), on(FRI_23_OCT, 15), wk(2, 11), wk(2, 9),
    ])

    assert message["text"].split("\n")[1] == (
        "Weekly Tue 09:00 · Weekly Tue 11:00 · Weekly Sun 09:00 · Fri 23 Oct 15:00 · Fri 25 Dec 10:00"
    )


def test_hours_already_watched_are_not_in_the_message(db):
    owner = member(db)
    weekly(db, owner, 2, 11)
    snapshot(db, {1: {(TUE_20_OCT, 11), (TUE_20_OCT, 12)}})

    message = save(db, owner, added=[wk(2, 11), wk(2, 12)])

    assert message["text"] == NEW_WATCHES + f"Weekly Tue 12:00\n\nTue 20 Oct 12:00  {link(1)}"


def test_nothing_free_on_the_added_hours_means_no_message(db):
    owner = member(db)
    weekly(db, owner, 2, 12)
    snapshot(db, {1: {(TUE_20_OCT, 12)}})

    assert save(db, owner, added=[wk(2, 11)]) is None
    assert db.one("select count(*) from alert") == 0


def test_slots_started_or_not_yet_open_are_left_out(db):
    owner = member(db)
    db.at("2026-10-14 10:30")
    snapshot(db, {1: {(date(2026, 10, 14), 10), (date(2026, 11, 18), 10), (date(2026, 11, 11), 10)}})

    message = save(db, owner, added=[wk(3, 10)])

    assert message["text"] == NEW_WATCHES + f"Weekly Wed 10:00\n\nWed 11 Nov 10:00  {link(1)}"


def test_a_save_with_nothing_added_sends_nothing(db):
    owner = member(db)
    weekly(db, owner, 2, 11)
    snapshot(db, {1: {(TUE_20_OCT, 11)}})

    assert save(db, owner, removed=[wk(2, 11)]) is None


# --- the 30-minute rule ---------------------------------------------------

def test_the_message_ignores_the_30_minute_rule(db):
    owner = member(db)
    single(db, owner, TUE_20_OCT, 11)
    db.call("record_scan", all_courts())
    [cancellation] = scan(db, "2026-10-14 09:05", {1: {(TUE_20_OCT, 11)}})
    sent(db, cancellation)
    db.at("2026-10-14 09:10")

    message = save(db, owner, added=[wk(2, 11)])

    assert message["text"] == NEW_WATCHES + f"Weekly Tue 11:00\n\nTue 20 Oct 11:00  {link(1)}"


def test_a_slot_with_an_alert_still_pending_is_left_to_that_alert(db):
    owner = member(db)
    single(db, owner, TUE_20_OCT, 11)
    db.call("record_scan", all_courts())
    [cancellation] = scan(db, "2026-10-14 09:05", {1: {(TUE_20_OCT, 11), (TUE_27_OCT, 11)}})
    failed(db, cancellation)

    message = save(db, owner, added=[wk(2, 11)])

    assert message["text"] == NEW_WATCHES + f"Weekly Tue 11:00\n\nTue 27 Oct 11:00  {link(1)}"
    sent(db, message)
    [retry] = scan(db, "2026-10-14 09:10", {1: {(TUE_20_OCT, 11), (TUE_27_OCT, 11)}})
    assert retry["text"] == f"<b>🎾 Court free</b>\n\nTue 20 Oct 11:00  {link(1)}"


def test_its_slots_then_count_toward_the_rule(db):
    owner = member(db)
    snapshot(db, {1: {(TUE_20_OCT, 11)}})
    sent(db, save(db, owner, added=[wk(2, 11)]))

    assert scan(db, "2026-10-14 09:10") == []
    assert scan(db, "2026-10-14 09:20", {1: {(TUE_20_OCT, 11)}}) == []
    assert scan(db, "2026-10-14 09:25") == []
    assert len(scan(db, "2026-10-14 09:31", {1: {(TUE_20_OCT, 11)}})) == 1


def test_a_failed_new_watch_message_is_retried_by_the_next_scan(db):
    owner = member(db)
    snapshot(db, {1: {(TUE_20_OCT, 11)}})
    message = save(db, owner, added=[wk(2, 11)])
    failed(db, message)

    [retry] = scan(db, "2026-10-14 09:05", {1: {(TUE_20_OCT, 11)}})

    assert retry == {
        "chat_id": OWNER,
        "text": f"<b>🎾 Free now</b>\n\nTue 20 Oct 11:00  {link(1)}",
        "alert_ids": message["alert_ids"],
    }


# --- the state the site reads ---------------------------------------------

def test_the_state_carries_watches_availability_the_last_check_and_window_end(db):
    owner = member(db)
    weekly(db, owner, 2, 11)
    single(db, owner, FRI_23_OCT, 15)
    db.at("2026-10-14 08:55")
    db.call("record_scan", all_courts(c2=court(2, free={(date(2026, 10, 15), 10)})))
    db.at("2026-10-14 09:00")

    state = db.call("member_state", owner)

    assert state["member"] == {"first_name": "Owner", "username": None, "is_owner": False}
    assert state["watches"] == [
        {"weekday": 2, "date": None, "hour": 11},
        {"weekday": None, "date": "2026-10-23", "hour": 15},
    ]
    assert state["unreachable_since"] is None
    assert state["last_check"] == "2026-10-14T08:55:00"
    assert state["window_end"] == "2026-11-17"
    assert {"date": "2026-10-15", "hour": 10, "free_courts": [2], "status": "free"} in state["availability"]
    assert state["availability"][0] == {"date": "2026-10-14", "hour": 10, "free_courts": [], "status": "booked"}


def test_the_state_carries_7_weeks_of_availability(db):
    member(db)
    db.at("2026-10-14 08:55")
    db.call("record_scan", all_courts(**{f"c{n}": court(n, days=60) for n in (1, 2, 3)}))
    db.at("2026-10-14 09:00")

    availability = db.call("member_state", db.one("select id from member"))["availability"]

    assert availability[-1]["date"] == "2026-12-01"  # 14 Oct + 48


def test_the_last_check_is_the_last_successful_court(db):
    owner = member(db)
    db.at("2026-10-14 08:55")
    db.call("record_scan", all_courts())
    db.at("2026-10-14 09:00")
    db.call("record_scan", all_courts(c1=court(1, weeks=5), c2=court(2, weeks=5), c3=court(3, weeks=5)))

    assert db.call("member_state", owner)["last_check"] == "2026-10-14T08:55:00"


def test_the_state_says_when_the_bot_stopped_reaching_the_member(db):
    owner = member(db)
    db.conn.execute("update member set unreachable_since = '2026-10-13 18:00' where id = %s", [owner])

    state = db.call("member_state", owner)

    assert state["unreachable_since"] == "2026-10-13T18:00:00"
    assert state["last_check"] is None
    assert state["availability"] == []
    assert state["watches"] == []


def test_another_members_watches_are_not_in_the_state(db):
    owner = member(db)
    weekly(db, member(db, 222, "Friend"), 2, 11)

    assert db.call("member_state", owner)["watches"] == []


def test_the_new_state_shows_a_saved_batch(db):
    owner = member(db)

    save(db, owner, added=[wk(6, 9)])

    assert db.call("member_state", owner)["watches"] == [{"weekday": 6, "date": None, "hour": 9}]

