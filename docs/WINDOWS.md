# Windows portable application

1. Open the [latest GitHub Release](https://github.com/fishchipssss/codex-usage-dashboard/releases/latest).
2. Download `CodexUsageDashboard-Windows-x64.zip` and extract it to a folder you want to keep.
3. Double-click `CodexUsageDashboard.exe`. The dashboard opens in your default browser at `http://127.0.0.1:8765/`.
4. Optionally right-click the EXE and use **Show more options > Send to > Desktop (create shortcut)**.

无需打开 Codex、PowerShell，也无需安装 Python 或 Node.js。下载 ZIP，解压后双击 EXE 即可。可以给 EXE 创建桌面快捷方式。

This is a Windows x64 portable launcher with its own bundled Python runtime. It starts the existing web dashboard; it does not embed a separate browser engine. It requires Windows 10/11 x64 and local Codex session logs to show usage. Git is optional for Git worktree grouping.

Repeated launches reuse a compatible running dashboard. An unrelated service on port 8765 is left alone and an error is displayed. Closing the browser tab leaves the local server running. To stop the portable server, end `CodexUsageDashboard.exe` in Task Manager. After restarting Windows, double-click the EXE again. No startup task or administrator privileges are required.

The application reads your local `.codex` sessions and uses the same multi-home configuration and local cache as the skill. Existing `%APPDATA%\cousash\sources.json` remains in use. Runtime logs are stored in `%APPDATA%\cousash\desktop.log`. No sessions, credentials, databases or personal configuration are bundled or uploaded. The EXE uses serial parsing for compatibility with its bundled runtime.

The release is unsigned; Windows may display a reputation warning. Check the repository, release and SHA-256 before choosing whether to run it. Release archives include the original MIT notice and Python/PyInstaller license texts. These are also embedded in the executable.

## Build from source

On Windows with Python 3.12 x64:

```powershell
python -m pip install pyinstaller==6.20.0
python tools/build_windows.py
python tools/smoke_windows.py dist/CodexUsageDashboard.exe
```

The smoke check uses synthetic data and requires port 8765 to be free. It never terminates an existing service. Build output stays in ignored `build/` and `dist/` directories. Only selected application code, the icon and license texts are included. See [PyInstaller's runtime guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html) for the independent frozen subprocess setup.
