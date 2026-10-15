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


def test_other_roles_cannot_log_anyone_in(db):
    db.conn.execute("create role stranger")
    db.conn.execute("set local role stranger")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call("login", {"id": 111, "first_name": "Owner"}, None)


def test_other_roles_cannot_read_a_members_state(db):
    db.conn.execute("create role stranger")
    db.conn.execute("set local role stranger")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call("member_state", 1)


def test_every_table_denies_anonymous_access(db):
    """RLS on with no policies: only service_role, which bypasses RLS, sees a row."""
    tables = db.rows(
        "select c.relname, c.relrowsecurity from pg_class c"
        " where c.relnamespace = 'public'::regnamespace and c.relkind = 'r'"
    )
    policies = db.one("select count(*) from pg_policies where schemaname = 'public'")

    assert tables and all(rls for _, rls in tables), tables
    assert policies == 0


def test_other_roles_cannot_save_watches(db):
    db.conn.execute("create role stranger")
    db.conn.execute("set local role stranger")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.call("save_watches", 1, [{"weekday": 2, "hour": 11}], [])


def test_other_roles_cannot_read_availability(db):
    """A view runs as its owner unless told otherwise, which would get round RLS."""
    db.call("record_scan", all_courts())
    db.conn.execute("create role stranger")
    db.conn.execute("grant select on availability to stranger")  # as Supabase's defaults do for anon
    db.conn.execute("set local role stranger")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.one("select count(*) from availability")


def test_other_roles_cannot_housekeep(db):
    db.conn.execute("create role stranger")
    db.conn.execute("set local role stranger")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.one("select housekeep()")
