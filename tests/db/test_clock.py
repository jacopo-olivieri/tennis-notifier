from datetime import date, datetime


def test_london_now_follows_the_pinned_clock(db):
    db.at("2026-10-25 01:30")

    assert db.one("select london_now()") == datetime(2026, 10, 25, 1, 30)


def test_london_now_falls_back_to_the_real_clock_in_london(db):
    db.conn.execute("select set_config('app.now', '', true)")

    assert db.one("select london_now() = (now() at time zone 'Europe/London')")


def test_window_end_is_34_days_after_london_today(db):
    db.at("2026-10-14 23:59")
    assert db.one("select window_end()") == date(2026, 11, 17)

    db.at("2026-10-15 00:00:10")
    assert db.one("select window_end()") == date(2026, 11, 18)
