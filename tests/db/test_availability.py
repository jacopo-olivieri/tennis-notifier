from datetime import date

from tests.db.test_record_scan import HOURS, all_courts, court

THU_15_OCT = date(2026, 10, 15)
WINDOW_END = date(2026, 11, 17)  # 14 Oct + 34


def availability(db, day, hour):
    return db.rows("select free_courts, status from availability where date = %s and hour = %s", [day, hour])


def test_an_hour_with_a_court_free_is_free_and_names_the_free_courts(db):
    db.call("record_scan", all_courts(
        c1=court(1, free={(THU_15_OCT, 10)}),
        c3=court(3, free={(THU_15_OCT, 10)}),
    ))

    assert availability(db, THU_15_OCT, 10) == [([1, 3], "free")]


def test_an_hour_with_every_court_booked_is_booked(db):
    db.call("record_scan", all_courts())

    assert availability(db, THU_15_OCT, 10) == [([], "booked")]


def test_an_hour_no_court_runs_that_day_is_no_session(db):
    dusk = {(THU_15_OCT, 17)}
    db.call("record_scan", all_courts(**{f"c{n}": court(n, missing=dusk) for n in (1, 2, 3)}))

    assert availability(db, THU_15_OCT, 17) == [([], "no session")]
    assert availability(db, date(2026, 10, 16), 17) == [([], "booked")]


def test_an_hour_one_court_runs_is_still_a_session(db):
    db.call("record_scan", all_courts(
        c1=court(1, missing={(THU_15_OCT, 17)}),
        c2=court(2, missing={(THU_15_OCT, 17)}),
    ))

    assert availability(db, THU_15_OCT, 17) == [([], "booked")]


def test_days_after_window_end_are_not_open_even_when_the_grid_shows_them_free(db):
    free = {(WINDOW_END, 10), (date(2026, 11, 18), 10)}
    db.call("record_scan", all_courts(c2=court(2, free=free)))

    assert availability(db, WINDOW_END, 10) == [([2], "free")]
    assert availability(db, date(2026, 11, 18), 10) == [([], "not open")]
    assert availability(db, date(2026, 11, 18), 11) == [([], "not open")]


def test_a_day_after_window_end_with_no_session_at_an_hour_is_still_no_session(db):
    dusk = {(date(2026, 11, 18), 17)}
    db.call("record_scan", all_courts(**{f"c{n}": court(n, missing=dusk) for n in (1, 2, 3)}))

    assert availability(db, date(2026, 11, 18), 17) == [([], "no session")]


def test_the_window_end_moves_with_the_clock(db):
    db.call("record_scan", all_courts(c2=court(2, free={(date(2026, 11, 18), 10)})))
    db.at("2026-10-15 00:00")

    assert availability(db, date(2026, 11, 18), 10) == [([2], "free")]


def test_only_hours_that_havent_started_are_listed(db):
    db.at("2026-10-14 09:00")
    db.call("record_scan", all_courts(c1=court(1, free={(date(2026, 10, 14), 9)})))

    today = db.rows("select hour from availability where date = '2026-10-14' order by hour")
    assert [h for (h,) in today] == list(range(10, 18))
    assert db.one("select min(date) from availability") == date(2026, 10, 14)


def test_every_scanned_day_and_hour_has_one_row(db):
    db.call("record_scan", all_courts())

    days = db.one("select count(distinct date) from availability")
    assert days == 42 - 3  # 11 Oct to 21 Nov, from today
    assert db.one("select count(*) from availability") == days * len(HOURS) - 2  # 08:00 and 09:00 today have started


def test_nothing_is_available_before_the_first_scan(db):
    assert db.one("select count(*) from availability") == 0
