from datetime import date, datetime

from tests.db.test_cancellation_alerts import member, single, weekly

NOW = "2026-10-15 03:00"
THU_15_OCT = date(2026, 10, 15)


def all_watches(db):
    return db.rows("select weekday, date, hour from watch order by id")


def slot(db, day, hour, court=1):
    db.conn.execute(
        "insert into slot (court, date, hour, status, status_since, last_seen_at)"
        " values (%s, %s, %s, 'free', '2026-10-01', '2026-10-01')",
        [court, day, hour],
    )


def expiring_invite(db, expires_at, used_by=None, revoked_at=None):
    db.conn.execute(
        "insert into invite (token_hash, created_at, expires_at, used_by, used_at, revoked_at)"
        " values (gen_random_uuid()::text, '2026-10-01', %s, %s, %s, %s)",
        [expires_at, used_by, "2026-10-03" if used_by else None, revoked_at],
    )


def logged(db, owner, at):
    """One alert, slot_change and scan_log row at `at`."""
    db.conn.execute(
        "insert into alert (member_id, court, date, hour, kind, created_at) values (%s, 1, %s, 10, 'release', %s)",
        [owner, THU_15_OCT, at],
    )
    db.conn.execute(
        "insert into slot_change (court, date, hour, from_status, to_status, at)"
        " values (1, %s, 10, 'booked', 'free', %s)",
        [THU_15_OCT, at],
    )
    db.conn.execute("insert into scan_log (at, court, ok, slots) values (%s, 1, true, 100)", [at])


def logs(db):
    return {
        table: [r[0] for r in db.rows(f"select {column} from {table} order by id")]
        for table, column in [("alert", "created_at"), ("slot_change", "at"), ("scan_log", "at")]
    }


def housekeep(db):
    db.at(NOW)
    db.one("select housekeep()")


def test_single_date_watches_go_once_their_hour_has_started(db):
    owner = member(db)
    single(db, owner, date(2026, 10, 14), 21)  # yesterday
    single(db, owner, THU_15_OCT, 2)  # earlier today
    single(db, owner, THU_15_OCT, 3)  # starting now
    single(db, owner, THU_15_OCT, 4)  # later today
    single(db, owner, date(2026, 12, 1), 10)  # not yet bookable

    housekeep(db)

    assert all_watches(db) == [(None, THU_15_OCT, 4), (None, date(2026, 12, 1), 10)]


def test_weekly_watches_are_kept(db):
    owner = member(db)
    weekly(db, owner, 3, 10)  # yesterday's weekday
    weekly(db, owner, 4, 2)  # today's, already past

    housekeep(db)

    assert all_watches(db) == [(3, None, 10), (4, None, 2)]


def test_past_slots_go_and_current_ones_stay(db):
    slot(db, date(2026, 10, 12), 18)
    slot(db, THU_15_OCT, 2, court=2)
    slot(db, THU_15_OCT, 3, court=3)
    slot(db, THU_15_OCT, 4)
    slot(db, date(2026, 11, 25), 9)  # stored, not open yet

    housekeep(db)

    assert db.rows("select court, date, hour from slot order by date, hour") == [
        (1, THU_15_OCT, 4),
        (1, date(2026, 11, 25), 9),
    ]


def test_expired_invites_go_whether_or_not_they_were_used(db):
    friend = member(db, 222, "Friend")
    expiring_invite(db, "2026-10-08 09:00")
    expiring_invite(db, "2026-10-09 09:00", used_by=friend)
    expiring_invite(db, "2026-10-10 09:00", revoked_at="2026-10-04")
    expiring_invite(db, NOW)
    expiring_invite(db, "2026-10-15 03:01")
    expiring_invite(db, "2026-10-20 09:00", used_by=friend)
    expiring_invite(db, "2026-10-21 09:00", revoked_at="2026-10-14")

    housekeep(db)

    assert db.rows("select expires_at from invite order by expires_at") == [
        (datetime(2026, 10, 15, 3, 1),),
        (datetime(2026, 10, 20, 9, 0),),
        (datetime(2026, 10, 21, 9, 0),),
    ]


def test_alerts_changes_and_scan_logs_older_than_30_days_go(db):
    owner = member(db)
    logged(db, owner, "2026-09-01 12:00")
    logged(db, owner, "2026-09-15 02:59")
    logged(db, owner, "2026-09-15 03:00")  # exactly 30 days
    logged(db, owner, "2026-10-14 23:55")

    housekeep(db)

    kept = [datetime(2026, 9, 15, 3, 0), datetime(2026, 10, 14, 23, 55)]
    assert logs(db) == {"alert": kept, "slot_change": kept, "scan_log": kept}


def test_members_and_markers_are_left_alone(db):
    owner = member(db)
    db.conn.execute("update member set joined_at = '2025-01-01' where id = %s", [owner])
    db.conn.execute(
        "insert into marker (kind, for_date, claimed_by, claimed_at, done_at)"
        " values ('release', '2026-09-01', 'run', '2026-08-31 23:45', '2026-09-01 00:01')"
    )

    housekeep(db)

    assert db.one("select count(*) from member") == 1
    assert db.one("select count(*) from marker") == 1


def test_housekeeping_twice_is_harmless(db):
    owner = member(db)
    single(db, owner, date(2026, 10, 14), 21)
    logged(db, owner, "2026-09-01 12:00")

    housekeep(db)
    housekeep(db)

    assert all_watches(db) == []
    assert logs(db) == {"alert": [], "slot_change": [], "scan_log": []}

