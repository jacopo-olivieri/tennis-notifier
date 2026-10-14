import psycopg
import pytest

from tests.db.test_record_scan import all_courts


def test_service_role_can_record_a_scan(db):
    db.conn.execute("set local role service_role")

    assert db.call("record_scan", all_courts())["all_complete"] is True


def test_other_roles_cannot_record_a_scan(db):
    db.conn.execute("create role stranger")
    db.conn.execute("set local role stranger")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call("record_scan", all_courts())


def test_functions_added_later_are_callable_by_service_role_only(db):
    db.conn.execute("create function added_later() returns int language sql as 'select 1'")
    db.conn.execute("create role stranger")

    db.conn.execute("set local role service_role")
    assert db.one("select added_later()") == 1

    db.conn.execute("reset role")
    db.conn.execute("set local role stranger")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.one("select added_later()")
