"""Harness for the SQL functions: a real Postgres with supabase/migrations applied.

Each test runs in one transaction that is rolled back, with the clock pinned
through app.now. Point DATABASE_URL at any Postgres 16 with the migrations
applied (CI uses a postgres:16 service container).
"""

import os

import psycopg
import pytest
from psycopg.types.json import Jsonb

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
START = "2026-10-14 09:00"


class Db:
    def __init__(self, conn):
        self.conn = conn

    def at(self, moment):
        """Pin london_now() for the rest of the test."""
        self.conn.execute("select set_config('app.now', %s, true)", [moment])

    def one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()[0]

    def rows(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def call(self, function, *args):
        """Call a SQL function, passing dicts and lists as jsonb."""
        args = [Jsonb(a) if isinstance(a, (dict, list)) else a for a in args]
        placeholders = ", ".join(["%s"] * len(args))
        return self.one(f"select {function}({placeholders})", args)


@pytest.fixture
def db():
    conn = psycopg.connect(DATABASE_URL)
    try:
        d = Db(conn)
        d.at(START)
        yield d
    finally:
        conn.rollback()
        conn.close()
