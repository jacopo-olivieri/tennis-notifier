from tests.db.test_cancellation_alerts import OWNER, member


def telegram_user(telegram_id=OWNER, first_name="Jacopo", username="jacopo"):
    """The Login Widget's user fields, as the Edge Function passes them on once verified."""
    user = {"id": telegram_id, "first_name": first_name, "auth_date": 1792000000}
    if username is not None:
        user["username"] = username
    return user


def test_a_member_logs_in_and_their_name_and_username_are_refreshed(db):
    owner = member(db, OWNER, "Old name")

    result = db.call("login", telegram_user(OWNER, "Jacopo", "jacopo"), None)

    assert result == {"status": "member", "member_id": owner}
    assert db.rows("select first_name, username from member where id = %s", [owner]) == [("Jacopo", "jacopo")]


def test_a_member_who_dropped_their_username_loses_it(db):
    owner = member(db)
    db.call("login", telegram_user(username="jacopo"), None)

    db.call("login", telegram_user(username=None), None)

    assert db.one("select username from member where id = %s", [owner]) is None


def test_someone_who_isnt_a_member_is_told_so_and_nothing_is_stored(db):
    member(db, OWNER, "Owner")

    result = db.call("login", telegram_user(999, "Stranger", "stranger"), None)

    assert result == {"status": "not_member"}
    assert db.rows("select telegram_id, first_name from member") == [(OWNER, "Owner")]


def test_an_invite_token_doesnt_make_a_stranger_a_member_yet(db):
    result = db.call("login", telegram_user(999, "Stranger"), "some-invite-token")

    assert result == {"status": "not_member"}
    assert db.one("select count(*) from member") == 0


def test_the_state_names_the_member_and_whether_they_are_the_owner(db):
    owner = member(db)
    db.conn.execute("update member set is_owner = true, username = 'jacopo' where id = %s", [owner])
    friend = member(db, 222, "Friend")

    assert db.call("member_state", owner)["member"] == {"first_name": "Owner", "username": "jacopo", "is_owner": True}
    assert db.call("member_state", friend)["member"] == {"first_name": "Friend", "username": None, "is_owner": False}


def test_a_removed_member_has_no_state(db):
    owner = member(db)
    db.conn.execute("delete from member where id = %s", [owner])

    assert db.call("member_state", owner) is None
