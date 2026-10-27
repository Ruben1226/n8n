import io
import json
import os

from collector import claude_hook, install_hooks
from conftest import ORIGIN, hook_records

SENSITIVE = ("tool_input", "tool_response", "last_assistant_message", "transcript_path", "redactado")


def test_normalize_keeps_only_metadata(payloads):
    for rec in hook_records():
        blob = json.dumps(rec)
        for word in SENSITIVE:
            assert word not in blob, (word, rec["event_type"])
        for key in ("prompt", "error"):
            assert key not in rec and key not in rec["meta"]
        assert rec["source"] == "hook"
        assert rec["origin"] == ORIGIN


def test_normalize_maps_real_fields(payloads):
    recs = {r["event_type"]: r for r in hook_records()}
    assert recs["SessionStart"]["meta"]["source"] == "startup"
    assert recs["PreToolUse"]["tool_name"] == "Bash"
    assert recs["PreToolUse"]["tool_use_id"].startswith("toolu_")
    assert recs["PostToolUseFailure"]["meta"]["is_error"] is True
    assert recs["PostToolUseFailure"]["meta"]["is_interrupt"] is False
    assert recs["SubagentStart"]["agent_id"] == "a0d5980ec0cf098e7"
    assert recs["SubagentStop"]["meta"]["background_running"] == 1
    assert recs["SessionEnd"]["meta"]["reason"] == "other"


def test_normalize_rejects_payload_without_event():
    assert claude_hook.normalize({"session_id": "x"}, ORIGIN) is None


def test_append_is_jsonl(tmp_path):
    rec = hook_records()[0]
    path = claude_hook.append_event(rec, str(tmp_path / "events"))
    lines = open(path).read().splitlines()
    assert json.loads(lines[0])["event_id"] == rec["event_id"]
    assert oct(os.stat(path).st_mode)[-3:] == "600"


def test_main_never_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_OFFICE_DATA_DIR", str(tmp_path))
    for raw in (b"", b"not json", b"[1,2]", b'{"hook_event_name": 5}', b"\xff\xfe"):
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(raw)))
        assert claude_hook.main() == 0
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(json.dumps({"hook_event_name": "Stop", "session_id": "abc"}).encode())))
    assert claude_hook.main() == 0
    files = list((tmp_path / "events").glob("hooks-*.jsonl"))
    assert len(files) == 1 and "Stop" in files[0].read_text()
    assert (tmp_path / "collector.log").exists()


def test_detect_origin_shape():
    o = claude_hook.detect_origin()
    assert set(o) == {"entrypoint", "cloud", "tmux", "remote_control", "claude_pid", "claude_start"}


def test_remote_control_flag_detection():
    assert claude_hook._is_remote_control(["claude", "remote-control"])
    assert claude_hook._is_remote_control(["claude", "--remote-control", "mi-sesion"])
    assert claude_hook._is_remote_control(["claude", "--remote-control=x"])
    assert not claude_hook._is_remote_control(["claude", "-p", "hola"])


# ------------------------------------------------------------- installer
def test_install_preserves_foreign_hooks_and_is_idempotent():
    foreign = {"type": "command", "command": "~/.claude/stop-hook-git-check.sh"}
    settings = {"model": "x", "hooks": {"Stop": [{"matcher": "", "hooks": [foreign]}]}}
    cmd = install_hooks.hook_command("python3")
    once = install_hooks.merge_ours(json.loads(json.dumps(settings)), cmd)
    twice = install_hooks.merge_ours(json.loads(json.dumps(once)), cmd)
    assert once == twice
    assert once["model"] == "x"
    assert foreign in once["hooks"]["Stop"][0]["hooks"]
    assert set(install_hooks.EVENTS) <= set(once["hooks"])
    removed = install_hooks.strip_ours(json.loads(json.dumps(once)))
    assert removed == settings


def test_install_cli_backup_and_uninstall(tmp_path, capsys):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"permissions": {"allow": ["Bash"]}}))
    assert install_hooks.main(["--install", "--yes", "--settings", str(path)]) == 0
    assert list(tmp_path.glob("settings.json.bak-claude-office-*"))
    data = json.loads(path.read_text())
    assert "claude_hook.py" in json.dumps(data["hooks"]["PreToolUse"])
    assert install_hooks.main(["--status", "--settings", str(path)]) == 0
    assert install_hooks.main(["--uninstall", "--yes", "--settings", str(path)]) == 0
    assert json.loads(path.read_text()) == {"permissions": {"allow": ["Bash"]}}


def test_print_mode_does_not_touch_files(tmp_path, capsys):
    path = tmp_path / "settings.json"
    assert install_hooks.main(["--settings", str(path)]) == 0
    assert not path.exists()
    assert "SessionStart" in capsys.readouterr().out
