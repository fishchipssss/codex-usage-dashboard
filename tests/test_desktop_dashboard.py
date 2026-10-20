import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "codex-usage-dashboard" / "scripts"
sys.path.insert(0, str(SCRIPTS))
desktop = importlib.import_module("desktop_dashboard")


class DesktopLauncherTests(unittest.TestCase):
    def test_git_metadata_helpers_are_utf8_and_windowless(self):
        with patch.object(desktop.dashboard.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = " 演示工作区 \n"
            self.assertEqual(desktop.dashboard.run_text_quiet(["git", "status"]), "演示工作区")
            self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
            self.assertEqual(run.call_args.kwargs["creationflags"],
                             getattr(desktop.subprocess, "CREATE_NO_WINDOW", 0))

    def test_frozen_server_relaunches_executable_not_python(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", "app.exe"):
            self.assertEqual(desktop.server_command(["--codex-home", "synthetic"]),
                             ["app.exe", "--serve", "--codex-home", "synthetic"])

    def test_existing_service_opens_without_spawning(self):
        with patch.object(desktop.opener, "dashboard_running_url", return_value=desktop.URL), \
             patch.object(desktop.opener, "open_browser") as browser, \
             patch.object(desktop.subprocess, "Popen") as spawn:
            self.assertEqual(desktop.launch([]), 0)
            browser.assert_called_once_with(desktop.URL)
            spawn.assert_not_called()

    def test_unrelated_port_owner_is_never_replaced(self):
        with patch.object(desktop.opener, "dashboard_running_url", return_value=None), \
             patch.object(desktop.socket, "socket") as socket_factory, \
             patch.object(desktop.subprocess, "Popen") as spawn:
            socket_factory.return_value.__enter__.return_value.connect_ex.return_value = 0
            with self.assertRaisesRegex(RuntimeError, "incompatible"):
                desktop.launch([], no_browser=True)
            spawn.assert_not_called()

    def test_spawn_has_independent_frozen_environment_and_utf8(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(desktop, "log_path", return_value=Path(root) / "desktop.log"), \
             patch.object(desktop.opener, "dashboard_running_url", return_value=None), \
             patch.object(desktop.opener, "wait_for_dashboard_url", return_value=desktop.URL), \
             patch.object(desktop.opener, "open_browser") as browser, \
             patch.object(desktop.socket, "socket") as socket_factory, \
             patch.object(desktop.subprocess, "Popen") as spawn:
            socket_factory.return_value.__enter__.return_value.connect_ex.return_value = 1
            self.assertEqual(desktop.launch([], no_browser=True), 0)
            options = spawn.call_args.kwargs
            self.assertEqual(options["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
            self.assertEqual(options["env"]["PYTHONUTF8"], "1")
            browser.assert_not_called()

    def test_failed_child_reports_log_instead_of_opening_browser(self):
        with tempfile.TemporaryDirectory() as root, \
             patch.object(desktop, "log_path", return_value=Path(root) / "desktop.log"), \
             patch.object(desktop.opener, "dashboard_running_url", return_value=None), \
             patch.object(desktop.opener, "wait_for_dashboard_url", return_value=None), \
             patch.object(desktop.opener, "open_browser") as browser, \
             patch.object(desktop.socket, "socket") as socket_factory, \
             patch.object(desktop.subprocess, "Popen"):
            socket_factory.return_value.__enter__.return_value.connect_ex.return_value = 1
            with self.assertRaisesRegex(RuntimeError, "desktop.log"):
                desktop.launch([], no_browser=True)
            browser.assert_not_called()

    def test_unicode_paths_are_forwarded_as_separate_arguments(self):
        with patch.object(desktop, "launch", return_value=0) as launch:
            desktop.main(["--no-browser", "--codex-home", "C:/演示 资料", "--sources-config", "C:/测试 config.json"])
            self.assertEqual(launch.call_args.args[0],
                             ["--codex-home", str(Path("C:/演示 资料")), "--sources-config", str(Path("C:/测试 config.json"))])
            self.assertTrue(launch.call_args.kwargs["no_browser"])
