"""Exercise a real frozen EXE using synthetic data only, on fixed port 8765."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

URL = "http://127.0.0.1:8765/"
ROOT = Path(__file__).resolve().parents[1]


class SyntheticTemporaryDirectory(tempfile.TemporaryDirectory):
    def cleanup(self):
        target = Path(self.name).resolve()
        if target.parent != Path(tempfile.gettempdir()).resolve() or not target.name.startswith("dashboard-exe-smoke-"):
            raise RuntimeError("Unexpected synthetic cleanup path.")
        # Windows process termination can precede release of SQLite/AV handles.
        for attempt in range(40):
            try:
                return super().cleanup()
            except PermissionError:
                if attempt == 39:
                    raise
                time.sleep(0.25)


def get_json(endpoint):
    with urlopen(URL + endpoint, timeout=10) as response:
        return json.load(response)


def main():
    executable = Path(sys.argv[1]).resolve()
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8765)) == 0:
            raise SystemExit("Port 8765 already occupied; existing service left untouched.")
    with SyntheticTemporaryDirectory(prefix="dashboard-exe-smoke-") as temporary:
        root = Path(temporary).resolve()
        home = root / "synthetic home 测试"
        sessions = home / "sessions"
        sessions.mkdir(parents=True)
        rows = [
            {"timestamp": "2026-10-19T12:00:00Z", "type": "session_meta", "payload": {
                "id": "synthetic-desktop-smoke", "cwd": str(root / "demo project"), "model": "gpt-5"}},
            {"timestamp": "2026-10-19T12:01:00Z", "type": "event_msg", "payload": {
                "type": "token_count", "info": {"total_token_usage": {
                    "input_tokens": 80, "cached_input_tokens": 20, "output_tokens": 20, "total_tokens": 100}}}},
        ]
        rollout = sessions / "rollout-synthetic.jsonl"
        rollout.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        before = hashlib.sha256(rollout.read_bytes()).hexdigest()
        environment = os.environ.copy()
        environment.update(COUSASH_CONFIG_DIR=str(root / "config"), CODEX_HOME=str(home),
                           PYTHONUTF8="1", PYINSTALLER_RESET_ENVIRONMENT="1")
        process = subprocess.Popen([str(executable), "--no-browser", "--codex-home", str(home)], env=environment)
        server_pid = None
        try:
            deadline = time.monotonic() + 60
            while True:
                if process.poll() not in (None, 0):
                    raise RuntimeError("Frozen server exited before health check; inspect synthetic desktop.log.")
                try:
                    health = get_json("api/health")
                    break
                except (OSError, ValueError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Frozen server startup timed out.")
                    time.sleep(0.25)
            assert health["app"] == "codex-usage-dashboard"
            assert "standalone-desktop-v1" in health["features"]
            server_pid = health["process_id"]
            assert isinstance(server_pid, int) and server_pid > 0
            assert process.wait(timeout=60) == 0
            # The detached server must survive the initial one-file launcher.
            time.sleep(1)
            backend = ROOT / "skills" / "codex-usage-dashboard" / "scripts" / "codex_usage_dashboard.py"
            assert health["implementation_sha256"] == hashlib.sha256(backend.read_bytes()).hexdigest()
            with urlopen(URL, timeout=10) as response:
                assert response.status == 200 and b"<!doctype html>" in response.read().lower()
            snapshot = get_json("api/sessions?period=all")
            assert snapshot["summary"]["session_count"] == 1, snapshot["summary"]
            assert snapshot["summary"]["usage"]["total_tokens"] == 100, snapshot["summary"]
            # Exercise the normal launcher path and ensure it reuses the server.
            duplicate = subprocess.run([str(executable), "--no-browser"], env=environment, timeout=60)
            assert duplicate.returncode == 0
            assert get_json("api/health")["process_id"] == server_pid
            assert get_json("api/health")["implementation_sha256"] == health["implementation_sha256"]
            assert hashlib.sha256(rollout.read_bytes()).hexdigest() == before
            print("PASS: cold frozen launch, parent exit, health/source hash, HTML, Unicode path, synthetic usage, repeat launch, read-only logs")
        finally:
            if server_pid is not None:
                # Terminate only the process tree this smoke test just created.
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(server_pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                else:
                    import signal
                    os.kill(server_pid, signal.SIGTERM)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)


if __name__ == "__main__":
    main()
