"""Standalone Windows entry point; no installed Python or Codex app required."""
from __future__ import annotations

import argparse
import multiprocessing
import os
from pathlib import Path
import socket
import subprocess
import sys
import traceback

import codex_usage_dashboard as dashboard
import open_dashboard as opener

URL = "http://127.0.0.1:8765/"
DESKTOP_FEATURE = "standalone-desktop-v1"


def server_command(arguments: list[str]) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--serve", *arguments]
    return [sys.executable, str(Path(__file__).resolve()), "--serve", *arguments]


def log_path() -> Path:
    return dashboard.app_config_dir() / "desktop.log"


def serve(args: argparse.Namespace) -> int:
    # Use the existing analyzer and UI without invoking main(), whose CLI has
    # automatic port replacement. The desktop app never terminates other apps.
    configured, origins = dashboard.source_configuration(args.sources_config)
    sources = (dashboard.codex_sources_from_homes(args.codex_home) if args.codex_home
               else configured or dashboard.default_codex_sources())
    analyzer = dashboard.CodexUsageAnalyzer(
        sources, remote_store=dashboard.RemoteSnapshotStore(),
        persistent_cache=dashboard.PersistentParseCache(),
        parallel_workers=0, source_origins=origins,
    )
    # Serial parsing avoids spawning interpreter workers from a windowless EXE.
    if DESKTOP_FEATURE not in dashboard.DASHBOARD_FEATURES:
        dashboard.DASHBOARD_FEATURES.append(DESKTOP_FEATURE)
    try:
        with dashboard.FixedPortHTTPServer(("127.0.0.1", 8765), dashboard.make_handler(analyzer)) as server:
            server.serve_forever()
    finally:
        analyzer.close()
    return 0


def launch(arguments: list[str], *, no_browser: bool = False) -> int:
    running = opener.dashboard_running_url()
    if not running:
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", 8765)) == 0:
                raise RuntimeError("Port 8765 is occupied by an incompatible service. Close it and try again.")
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        # The server outlives this launcher, so it needs its own extraction dir.
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        target_log = log_path()
        target_log.parent.mkdir(parents=True, exist_ok=True)
        with target_log.open("ab") as output:
            process = subprocess.Popen(
                server_command(arguments), stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT, env=environment,
                creationflags=flags, close_fds=True,
            )
        running = opener.wait_for_dashboard_url(process, timeout=60)
        if not running:
            raise RuntimeError(f"Dashboard did not start. See {target_log}")
    if not no_browser:
        opener.open_browser(running)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the local Codex Usage Dashboard and open your browser.")
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-browser", action="store_true", help="Start without opening a browser.")
    parser.add_argument("--codex-home", type=Path, action="append")
    parser.add_argument("--sources-config", type=Path)
    args = parser.parse_args(argv)
    if args.serve:
        target_log = log_path()
        target_log.parent.mkdir(parents=True, exist_ok=True)
        with target_log.open("a", encoding="utf-8", buffering=1) as output:
            sys.stdout = sys.stderr = output
            try:
                return serve(args)
            except Exception:
                traceback.print_exc()
                return 1
    forwarded: list[str] = []
    for home in args.codex_home or []:
        forwarded.extend(["--codex-home", str(home)])
    if args.sources_config:
        forwarded.extend(["--sources-config", str(args.sources_config)])
    try:
        return launch(forwarded, no_browser=args.no_browser)
    except Exception as exc:
        if sys.platform == "win32" and not args.no_browser:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, str(exc), "Codex Usage Dashboard", 0x10)
        elif sys.stderr is not None:
            print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
