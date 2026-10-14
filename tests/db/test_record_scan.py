from datetime import date, datetime, timedelta

FIRST_DAY = date(2026, 10, 11)  # the Sunday starting the week of START
HOURS = range(8, 18)


def court(number, free=(), weeks=6, days=42, missing=(), error=None):
    """A scan_court result for one court: every slot booked except `free`."""
    slots = [
        {"date": (FIRST_DAY + timedelta(d)).isoformat(), "hour": h,
         "status": "free" if (FIRST_DAY + timedelta(d), h) in free else "booked"}
        for d in range(days)
        for h in HOURS
        if (FIRST_DAY + timedelta(d), h) not in missing
    ]
    result = {"court": number, "weeks": weeks, "slots": slots}
    if error:
        result["error"] = error
    return result


def all_courts(**overrides):
    return [overrides.get(f"c{n}", court(n)) for n in (1, 2, 3)]


def status(db, number, day, hour):
    return db.one("select status from slot where court = %s and date = %s and hour = %s", [number, day, hour])


def scan_log(db):
    return db.rows("select at, court, ok, slots, error from scan_log order by at, court")


def test_a_complete_scan_stores_every_slot_and_logs_each_court(db):
    free = {(date(2026, 10, 15), 11)}

    result = db.call("record_scan", all_courts(c2=court(2, free=free)))

    assert result["all_complete"] is True
    assert db.one("select count(*) from slot") == 3 * 420
    assert status(db, 2, date(2026, 10, 15), 11) == "free"
    assert status(db, 1, date(2026, 10, 15), 11) == "booked"
    at = datetime(2026, 10, 14, 9, 0)
    assert scan_log(db) == [(at, 1, True, 420, None), (at, 2, True, 420, None), (at, 3, True, 420, None)]
    assert db.rows("select * from slot_change") == []


def test_a_status_change_is_applied_and_logged(db):
    slot = (date(2026, 10, 20), 17)
    db.call("record_scan", all_courts())

    db.at("2026-10-14 09:05")
    db.call("record_scan", all_courts(c3=court(3, free={slot})))

    assert status(db, 3, *slot) == "free"
    assert db.one("select status_since from slot where court = 3 and date = %s and hour = %s", slot) == datetime(2026, 10, 14, 9, 5)
    assert db.one("select status_since from slot where court = 1 and date = %s and hour = %s", slot) == datetime(2026, 10, 14, 9, 0)
    assert db.one("select last_seen_at from slot where court = 1 and date = %s and hour = %s", slot) == datetime(2026, 10, 14, 9, 5)
    assert db.rows("select court, date, hour, from_status, to_status, at from slot_change") == [
        (3, *slot, "booked", "free", datetime(2026, 10, 14, 9, 5)),
    ]


def test_a_future_slot_missing_from_a_complete_scan_is_kept(db):
    slot = (date(2026, 10, 20), 10)
    db.call("record_scan", all_courts())

    db.at("2026-10-14 09:05")
    db.call("record_scan", all_courts(c1=court(1, missing={slot})))
    assert status(db, 1, *slot) == "booked"
    assert db.one("select last_seen_at from slot where court = 1 and date = %s and hour = %s", slot) == datetime(2026, 10, 14, 9, 0)

    db.at("2026-10-14 09:10")
    db.call("record_scan", all_courts(c1=court(1, free={slot})))
    assert status(db, 1, *slot) == "free"
    assert db.rows("select court, from_status, to_status from slot_change") == [(1, "booked", "free")]


def test_a_court_with_5_of_6_weeks_is_skipped_while_the_others_apply(db):
    slot = (date(2026, 10, 15), 11)
    db.call("record_scan", all_courts())

    db.at("2026-10-14 09:05")
    result = db.call("record_scan", [
        court(1, free={slot}, weeks=5, days=35, error="HTTPError 520"),
        court(2, free={slot}),
        court(3, free={slot}),
    ])

    assert result["all_complete"] is False
    assert status(db, 1, *slot) == "booked"
    assert db.one("select max(last_seen_at) from slot where court = 1") == datetime(2026, 10, 14, 9, 0)
    assert status(db, 2, *slot) == "free"
    assert status(db, 3, *slot) == "free"
    assert db.rows("select court from slot_change order by court") == [(2,), (3,)]
    at = datetime(2026, 10, 14, 9, 5)
    assert scan_log(db)[3:] == [
        (at, 1, False, 350, "HTTPError 520"),
        (at, 2, True, 420, None),
        (at, 3, True, 420, None),
    ]


def test_a_court_with_below_half_its_previous_slots_is_skipped(db):
    db.call("record_scan", all_courts())

    db.at("2026-10-14 09:05")
    half_gone = {(FIRST_DAY + timedelta(d), h) for d in range(42) for h in range(8, 14)}
    result = db.call("record_scan", all_courts(c2=court(2, missing=half_gone)))

    assert result["all_complete"] is False
    assert db.one("select max(last_seen_at) from slot where court = 2") == datetime(2026, 10, 14, 9, 0)
    assert db.one("select max(last_seen_at) from slot where court = 1") == datetime(2026, 10, 14, 9, 5)
    assert scan_log(db)[3:] == [
        (datetime(2026, 10, 14, 9, 5), 1, True, 420, None),
        (datetime(2026, 10, 14, 9, 5), 2, False, 168, "168 slots, below half of the previous 420"),
        (datetime(2026, 10, 14, 9, 5), 3, True, 420, None),
    ]


def test_exactly_half_the_previous_slots_still_counts_as_complete(db):
    db.call("record_scan", all_courts())

    db.at("2026-10-14 09:05")
    half_gone = {(FIRST_DAY + timedelta(d), h) for d in range(42) for h in range(8, 13)}
    result = db.call("record_scan", all_courts(c2=court(2, missing=half_gone)))

    assert result["all_complete"] is True


def test_a_court_missing_from_the_scan_means_not_all_complete(db):
    result = db.call("record_scan", [court(1), court(2)])

    assert result["all_complete"] is False


def test_a_court_whose_slots_cannot_be_stored_is_logged_and_the_others_apply(db):
    bad = court(2)
    bad["slots"].append(bad["slots"][0])  # the same (date, hour) twice

    result = db.call("record_scan", all_courts(c2=bad))

    assert result["all_complete"] is False
    assert [f["court"] for f in result["failed"]] == [2]
    assert db.one("select count(*) from slot where court = 2") == 0
    assert db.one("select count(*) from slot") == 2 * 420
    log = scan_log(db)
    assert [(c, ok) for _, c, ok, _, _ in log] == [(1, True), (2, False), (3, True)]
    assert log[1][4].startswith("not recorded: ")


def test_a_clean_scan_reports_no_failures(db):
    assert db.call("record_scan", all_courts())["failed"] == []
