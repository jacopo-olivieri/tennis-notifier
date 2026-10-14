from notifier.health import should_ping

ALL_COMPLETE = {"all_complete": True}
ONE_INCOMPLETE = {"all_complete": False}


def test_pings_when_all_courts_complete_and_sends_succeed():
    assert should_ping(ALL_COMPLETE, [200, 200])


def test_pings_when_all_courts_complete_and_nothing_to_send():
    assert should_ping(ALL_COMPLETE, [])


def test_no_ping_when_one_court_is_incomplete():
    assert not should_ping(ONE_INCOMPLETE, [200])


def test_no_ping_when_record_scan_failed():
    assert not should_ping(None, [])


def test_no_ping_when_a_send_returned_401():
    assert not should_ping(ALL_COMPLETE, [200, 401, 403])


def test_a_403_alone_still_pings():
    assert should_ping(ALL_COMPLETE, [403, 200])


def test_other_send_failures_still_ping():
    assert should_ping(ALL_COMPLETE, [429, 500, None])
