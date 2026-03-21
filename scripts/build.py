import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "MediaManagerX.spec"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
APP_DIR = DIST_DIR / "MediaManagerX"
INTERNAL_DIR = APP_DIR / "_internal"
VERSION_FILE = ROOT / "VERSION"
RELEASE_NOTES_FILE = ROOT / "ReleaseNotes.md"


def create_icon() -> None:
    print("Generating app.ico from web logo...")
    img_path = ROOT / "native" / "mediamanagerx_app" / "web" / "media-manager-logo-256.png"
    if not img_path.exists():
        raise FileNotFoundError(f"Icon source not found: {img_path}")

    img = Image.open(img_path)
    try:
        img.save(
            ROOT / "app.ico",
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)],
        )
    finally:
        img.close()


def clean_build_dirs() -> None:
    for path in (DIST_DIR, BUILD_DIR):
        if path.exists():
            print(f"Removing stale build output: {path}")
            shutil.rmtree(path)


def build_exe() -> None:
    print("Building standalone executable with PyInstaller spec...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_PATH),
    ]
    print(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=ROOT)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def verify_bundle() -> str:
    expected_version = _read_text(VERSION_FILE).strip()
    bundled_version_path = INTERNAL_DIR / "VERSION"
    bundled_notes_path = INTERNAL_DIR / "ReleaseNotes.md"

    if not bundled_version_path.exists():
        raise FileNotFoundError(f"Bundled VERSION missing: {bundled_version_path}")
    if not bundled_notes_path.exists():
        raise FileNotFoundError(f"Bundled ReleaseNotes.md missing: {bundled_notes_path}")

    bundled_version = _read_text(bundled_version_path).strip()
    if bundled_version != expected_version:
        raise RuntimeError(
            f"Bundled version mismatch: expected {expected_version}, found {bundled_version}"
        )

    expected_notes = _read_text(RELEASE_NOTES_FILE)
    bundled_notes = _read_text(bundled_notes_path)
    if bundled_notes != expected_notes:
        raise RuntimeError("Bundled ReleaseNotes.md does not match the repo root copy.")

    exe_path = APP_DIR / "MediaManagerX.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Built executable missing: {exe_path}")

    print(f"Verified bundled version: {bundled_version}")
    return bundled_version


def find_iscc() -> Path:
    env_path = os.environ.get("ISCC_EXE")
    candidates = [
        Path(env_path) if env_path else None,
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise FileNotFoundError(
        "ISCC.exe not found. Set ISCC_EXE or install Inno Setup 6."
    )


def build_installer() -> None:
    iscc = find_iscc()
    iss_path = ROOT / "installer.iss"
    cmd = [str(iscc), str(iss_path)]
    print(f"Compiling installer: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build MediaManagerX release artifacts from the canonical spec."
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Compile MediaManagerX_Setup.exe after rebuilding and validating the app bundle.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Keep existing build/dist directories instead of deleting them first.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    create_icon()
    if not args.no_clean:
        clean_build_dirs()
    build_exe()
    verify_bundle()
    if args.installer:
        build_installer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
