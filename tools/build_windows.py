"""Build a Windows x64 portable executable from explicitly selected public files."""
import hashlib
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "codex-usage-dashboard" / "scripts"
NAME = "CodexUsageDashboard"


def main():
    if sys.platform != "win32":
        raise SystemExit("Build on Windows with Python 3.12 x64.")
    import PyInstaller.__main__
    dist = ROOT / "dist"
    build = ROOT / "build" / "windows"
    licenses = build / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE", licenses / "APP-MIT.txt")
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", licenses / "PYTHON.txt")
    pyinstaller = distribution("pyinstaller")
    license_entry = next(p for p in pyinstaller.files if str(p).endswith("licenses/COPYING.txt"))
    shutil.copyfile(pyinstaller.locate_file(license_entry), licenses / "PYINSTALLER.txt")
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--onefile", "--windowed", "--noupx",
        "--name", NAME, "--distpath", str(dist), "--workpath", str(build / "work"),
        "--specpath", str(build), "--paths", str(SCRIPTS),
        "--python-option", "utf8",
        "--icon", str(SCRIPTS.parent / "assets" / "codex_usage_dashboard.ico"),
        # The health endpoint hashes the backend's source file at runtime.
        "--add-data", f"{SCRIPTS / 'codex_usage_dashboard.py'};.",
        "--add-data", f"{licenses};licenses",
        str(SCRIPTS / "desktop_dashboard.py"),
    ])
    archive = dist / f"{NAME}-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(dist / f"{NAME}.exe", f"{NAME}.exe")
        bundle.write(ROOT / "docs" / "WINDOWS.md", "README.md")
        for path in sorted(licenses.iterdir()):
            bundle.write(path, f"licenses/{path.name}")
    artifacts = [dist / f"{NAME}.exe", archive]
    (dist / "SHA256SUMS.txt").write_text(
        "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in artifacts), encoding="utf-8",
    )
    print("Built portable EXE, ZIP and SHA256SUMS.txt in dist/.")


if __name__ == "__main__":
    main()
