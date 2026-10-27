import json

from backend.domain.event_normalizer import MAX_LINE_BYTES, normalize_line
from conftest import hook_records

NOW = 2_000_000_000.0


def test_real_records_normalize():
    for rec in hook_records():
        ev = normalize_line(json.dumps(rec), NOW)
        assert ev is not None
        assert ev["event_id"] == rec["event_id"]
        assert ev["known"] is True
        assert ev["origin"]["remote_control"] is True


def test_malformed_lines_are_dropped():
    bad = [
        "",
        "not json",
        "[]",
        '{"event_type": "Stop"}',  # sin event_id
        '{"event_id": "x", "event_type": "<script>"}',
        '{"event_id": "../../etc", "event_type": "Stop"}',
        '{"event_id": "a b", "event_type": "Stop"}',
    ]
    for line in bad:
        assert normalize_line(line, NOW) is None, line


def test_oversized_line_dropped():
    rec = {"event_id": "abc", "event_type": "Stop", "meta": {"cwd": "x" * MAX_LINE_BYTES}}
    assert normalize_line(json.dumps(rec), NOW) is None


def test_types_and_lengths_are_sanitized():
    rec = {
        "event_id": "abc",
        "event_type": "PreToolUse",
        "timestamp": "2999-01-01T00:00:00Z",  # futuro -> se usa now
        "session_id": "s1",
        "tool_name": "T" * 500,
        "meta": {"duration_ms": "lots", "is_interrupt": 1, "cwd": "/x", "unknown": "drop"},
        "origin": {"claude_pid": True, "remote_control": True},
        "source": "evil",
    }
    ev = normalize_line(json.dumps(rec), NOW)
    assert ev["ts"] == NOW
    assert len(ev["tool_name"]) == 64
    assert ev["meta"] == {"cwd": "/x"}
    assert ev["origin"] == {"remote_control": True}
    assert ev["source"] == "hook"


def test_unknown_event_type_kept_but_flagged():
    ev = normalize_line('{"event_id": "abc", "event_type": "FutureEvent"}', NOW)
    assert ev["known"] is False
