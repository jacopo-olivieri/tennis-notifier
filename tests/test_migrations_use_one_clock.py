"""london_now() is the only clock: no migration may read the time anywhere else."""

import re
from pathlib import Path

MIGRATIONS = sorted((Path(__file__).resolve().parent.parent / "supabase" / "migrations").glob("*.sql"))
LONDON_NOW = re.compile(r"create (or replace )?function london_now\(\).*?\$\$.*?\$\$", re.S | re.I)
CLOCK_READS = re.compile(
    r"\bnow\s*\(|\bcurrent_date\b|\bcurrent_time\b|\bcurrent_timestamp\b|\blocaltime\b|\blocaltimestamp\b"
    r"|\b(clock|statement|transaction)_timestamp\s*\(",
    re.I,
)


def test_migrations_read_the_time_only_through_london_now():
    assert MIGRATIONS
    offences = [
        f"{path.name}: {m.group(0)}"
        for path in MIGRATIONS
        for m in CLOCK_READS.finditer(LONDON_NOW.sub("", path.read_text()))
    ]
    assert offences == []
