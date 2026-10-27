import subprocess
import sys
import time

import pytest

from backend.domain.state_machine import Office
from backend.services import process_monitor

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="usa /proc")


def test_real_process_detected_and_marked_exited():
    child = subprocess.Popen(["sleep", "30"])
    try:
        procs = process_monitor.scan()
        me = [p for p in procs if p.pid == child.pid]
        assert me and me[0].comm == "sleep" and me[0].start_epoch > 0
        o = Office()
        o.process_scan(procs, time.time() + 10, ["sleep"], min_age=0)
        ents = [e for e in o.entities.values() if e.pid == child.pid]
        assert len(ents) == 1 and ents[0].status == "running"
    finally:
        child.kill()
        child.wait()
    o.process_scan(process_monitor.scan(), time.time() + 20, ["sleep"], min_age=0)
    assert ents[0].status == "exited"


def test_scan_never_records_arguments():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", "SECRET_TOKEN_123"])
    try:
        procs = process_monitor.scan(record_script_name=True)
        blob = repr([p for p in procs if p.pid == child.pid])
        assert "SECRET_TOKEN_123" not in blob
    finally:
        child.kill()
        child.wait()
