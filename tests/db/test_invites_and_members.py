import hashlib
from datetime import date, datetime

import psycopg
import pytest

from tests.db.test_cancellation_alerts import OWNER, alerts, free_up, member, single, weekly
from tests.db.test_login import telegram_user

FRIEND = 222


def owner(db):
    owner_id = member(db, OWNER, "Jacopo")
    db.conn.execute("update member set is_owner = true where id = %s", [owner_id])
    return owner_id


def invite(db, owner_id):
    return db.call("create_invite", owner_id)


def redeem(db, token, telegram_id=FRIEND, first_name="Friend", username="friend"):
    return db.call("login", telegram_user(telegram_id, first_name, username), token)


# --- creating and redeeming ---------------------------------------------------


def test_an_invite_returns_its_raw_token_once_and_stores_only_its_hash(db):
    o = owner(db)

    created = invite(db, o)

    token = created["token"]
    assert len(token) >= 32
    stored = db.rows("select id, token_hash, created_at, expires_at from invite")
    assert stored == [(created["id"], hashlib.sha256(token.encode()).hexdigest(),
                       datetime(2026, 10, 14, 9, 0), datetime(2026, 10, 21, 9, 0))]
    assert token not in str(db.rows("select * from invite"))


def test_each_invite_has_its_own_token(db):
    o = owner(db)

    assert invite(db, o)["token"] != invite(db, o)["token"]


def test_a_valid_invite_makes_the_friend_a_member_and_is_used(db):
    o = owner(db)
    created = invite(db, o)
    db.at("2026-10-15 18:00")

    result = redeem(db, created["token"])

    friend = db.one("select id from member where telegram_id = %s", [FRIEND])
    assert result == {"status": "member", "member_id": friend}
    assert db.rows("select first_name, username, is_owner, joined_at from member where id = %s", [friend]) == [
        ("Friend", "friend", False, datetime(2026, 10, 15, 18, 0))
    ]
    assert db.rows("select used_by, used_at from invite") == [(friend, datetime(2026, 10, 15, 18, 0))]


def test_an_invite_works_only_once(db):
    token = invite(db, owner(db))["token"]
    redeem(db, token)

    result = redeem(db, token, 333, "Someone else")

    assert result == {"status": "invite_invalid"}
    assert db.one("select count(*) from member where telegram_id = 333") == 0


def test_an_invite_still_works_just_before_its_7_days_are_up(db):
    token = invite(db, owner(db))["token"]
    db.at("2026-10-21 08:59")

    assert redeem(db, token)["status"] == "member"


def test_an_invite_7_days_old_is_refused(db):
    token = invite(db, owner(db))["token"]
    db.at("2026-10-21 09:00")

    assert redeem(db, token) == {"status": "invite_invalid"}
    assert db.one("select count(*) from member") == 1


def test_a_revoked_invite_is_refused(db):
    o = owner(db)
    created = invite(db, o)

    db.call("revoke_invite", o, created["id"])

    assert db.one("select revoked_at from invite") == datetime(2026, 10, 14, 9, 0)
    assert redeem(db, created["token"]) == {"status": "invite_invalid"}
    assert db.one("select count(*) from member") == 1


def test_a_made_up_token_is_refused(db):
    owner(db)

    assert redeem(db, "not-a-real-token") == {"status": "invite_invalid"}
    assert db.one("select count(*) from member") == 1


def test_a_member_opening_an_invite_just_logs_in_and_leaves_it_unused(db):
    o = owner(db)
    token = invite(db, o)["token"]

    assert db.call("login", telegram_user(OWNER, "Jacopo"), token) == {"status": "member", "member_id": o}
    assert db.one("select used_at from invite") is None


def test_revoking_a_used_invite_changes_nothing(db):
    o = owner(db)
    created = invite(db, o)
    redeem(db, created["token"])

    db.call("revoke_invite", o, created["id"])

    assert db.one("select revoked_at from invite") is None


# --- the owner's lists --------------------------------------------------------


def test_outstanding_invites_leave_out_used_revoked_and_expired_ones(db):
    o = owner(db)
    used, revoked = invite(db, o), invite(db, o)
    redeem(db, used["token"])
    db.call("revoke_invite", o, revoked["id"])
    db.at("2026-10-15 10:00")
    fresh = invite(db, o)
    db.at("2026-10-21 09:30")  # the first two would have expired by now anyway

    assert db.call("list_invites", o) == [
        {"id": fresh["id"], "created_at": "2026-10-15T10:00:00", "expires_at": "2026-10-22T10:00:00"}
    ]


def test_members_are_listed_with_name_handle_and_hours_watched(db):
    o = owner(db)
    friend = redeem(db, invite(db, o)["token"], FRIEND, "Friend", None)["member_id"]
    weekly(db, friend, 2, 18)
    weekly(db, friend, 2, 19)
    single(db, friend, date(2026, 10, 24), 10)
    single(db, friend, date(2026, 10, 13), 10)  # past, so not counted
    single(db, friend, date(2026, 10, 14), 8)  # started, so not counted

    assert db.call("list_members", o) == [
        {"id": o, "first_name": "Jacopo", "username": None, "is_owner": True, "hours": 0},
        {"id": friend, "first_name": "Friend", "username": None, "is_owner": False, "hours": 3},
    ]


# --- removing a member --------------------------------------------------------


def test_removing_a_member_deletes_them_with_their_watches_and_alerts(db):
    o = owner(db)
    friend = redeem(db, invite(db, o)["token"])["member_id"]
    weekly(db, friend, 3, 10)
    weekly(db, o, 3, 10)
    free_up(db, {3: {(date(2026, 10, 14), 10)}})
    assert {a[0] for a in alerts(db)} == {o, friend}

    db.call("remove_member", o, friend)

    assert db.rows("select id from member") == [(o,)]
    assert db.rows("select member_id from watch") == [(o,)]
    assert {a[0] for a in alerts(db)} == {o}
    assert db.call("member_state", friend) is None
    assert db.one("select used_by from invite") is None


def test_a_removed_member_cannot_log_back_in(db):
    o = owner(db)
    friend = redeem(db, invite(db, o)["token"])["member_id"]

    db.call("remove_member", o, friend)

    assert db.call("login", telegram_user(FRIEND, "Friend"), None) == {"status": "not_member"}


def test_the_owner_cannot_remove_themselves(db):
    o = owner(db)

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call("remove_member", o, o)


# --- owner only ---------------------------------------------------------------


@pytest.mark.parametrize("function, args", [
    ("create_invite", ()),
    ("revoke_invite", (1,)),
    ("list_invites", ()),
    ("list_members", ()),
    ("remove_member", (1,)),
])
def test_owner_only_functions_refuse_a_member_who_isnt_the_owner(db, function, args):
    owner(db)
    friend = member(db, FRIEND, "Friend")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call(function, friend, *args)


def test_a_member_who_isnt_the_owner_cannot_revoke_or_remove(db):
    o = owner(db)
    created = invite(db, o)
    friend = redeem(db, invite(db, o)["token"])["member_id"]

    for call in [lambda: db.call("revoke_invite", friend, created["id"]), lambda: db.call("remove_member", friend, o)]:
        db.conn.execute("savepoint s")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            call()
        db.conn.execute("rollback to savepoint s")

    assert db.one("select revoked_at from invite where id = %s", [created["id"]]) is None
    assert db.one("select count(*) from member") == 2


def test_a_removed_owner_id_is_refused(db):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call("create_invite", 12345)
