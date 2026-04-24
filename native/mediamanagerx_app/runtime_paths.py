from __future__ import annotations

from native.mediamanagerx_app.common import *

def _dpi_awareness_context_handle(value: int):
    mask = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
    return ctypes.c_void_p(value & mask)


def _describe_windows_dpi_awareness() -> str:
    if os.name != "nt":
        return "non-windows"

    user32 = getattr(ctypes.windll, "user32", None)
    if user32 is not None:
        try:
            get_thread_context = user32.GetThreadDpiAwarenessContext
            get_thread_context.restype = wintypes.HANDLE
            are_equal = user32.AreDpiAwarenessContextsEqual
            are_equal.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            are_equal.restype = wintypes.BOOL
            current = get_thread_context()
            known_contexts = (
                ("unaware", -1),
                ("system", -2),
                ("permonitor", -3),
                ("permonitorv2", -4),
                ("unawaregdiscaled", -5),
            )
            for name, raw_value in known_contexts:
                if are_equal(current, _dpi_awareness_context_handle(raw_value)):
                    return name
        except Exception:
            pass

    shcore = getattr(ctypes.windll, "shcore", None)
    if shcore is not None:
        try:
            awareness = ctypes.c_int(-1)
            get_process_awareness = shcore.GetProcessDpiAwareness
            get_process_awareness.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_int)]
            get_process_awareness.restype = ctypes.c_long
            result = get_process_awareness(None, ctypes.byref(awareness))
            if result == 0:
                return {
                    0: "unaware",
                    1: "system",
                    2: "permonitor",
                }.get(int(awareness.value), f"unknown({awareness.value})")
        except Exception:
            pass

    return "unknown"


def _describe_qt_dpi_policy() -> str:
    try:
        policy = QApplication.highDpiScaleFactorRoundingPolicy()
        names = {
            Qt.HighDpiScaleFactorRoundingPolicy.Round: "Round",
            Qt.HighDpiScaleFactorRoundingPolicy.Ceil: "Ceil",
            Qt.HighDpiScaleFactorRoundingPolicy.Floor: "Floor",
            Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor: "RoundPreferFloor",
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough: "PassThrough",
        }
        return names.get(policy, str(policy))
    except Exception:
        return "unknown"


def _format_dpi_state(app: QApplication | None = None) -> str:
    if app is None:
        try:
            app = QApplication.instance()
        except Exception:
            app = None

    awareness = _describe_windows_dpi_awareness()
    qt_policy = _describe_qt_dpi_policy()
    screen_parts: list[str] = []
    if app is not None:
        for screen in app.screens():
            try:
                geometry = screen.geometry()
                screen_parts.append(
                    f"{screen.name()}: dpr={screen.devicePixelRatio():.2f}, "
                    f"logical={screen.logicalDotsPerInch():.2f}, "
                    f"physical={screen.physicalDotsPerInch():.2f}, "
                    f"geom={geometry.width()}x{geometry.height()}@{geometry.x()},{geometry.y()}"
                )
            except Exception:
                continue
    screens_text = "; ".join(screen_parts) if screen_parts else "none"
    return (
        "DPI: "
        f"windows_awareness={awareness}, "
        f"qt_rounding_policy={qt_policy}, "
        f"screens=[{screens_text}]"
    )


def _log_dpi_state(app: QApplication, log) -> None:
    try:
        log(_format_dpi_state(app))
    except Exception:
        pass


def _run_hidden_subprocess(cmd: list[str], **kwargs):
    if _WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS:
        kwargs = {**_WINDOWS_NO_CONSOLE_SUBPROCESS_KWARGS, **kwargs}
    return subprocess.run(cmd, **kwargs)


_FAULT_HANDLER_STREAM = None
_SETTINGS_MIGRATED = False
_APPDATA_DIRS_MIGRATED = False


def _paths_same(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except Exception:
        return os.path.abspath(str(left)) == os.path.abspath(str(right))


def _unique_legacy_copy_path(path: Path) -> Path:
    stem = path.stem
    suffix = path.suffix
    for idx in range(1, 1000):
        candidate = path.with_name(f"{stem}.legacy-{idx}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}.legacy-{int(time.time())}{suffix}")


def _merge_directory_contents(source: Path, target: Path) -> bool:
    if not source.exists() or not source.is_dir() or _paths_same(source, target):
        return True

    ok = True
    try:
        target.mkdir(parents=True, exist_ok=True)
        entries = list(source.iterdir())
    except Exception:
        return False

    for child in entries:
        dest = target / child.name
        try:
            if child.is_dir():
                ok = _merge_directory_contents(child, dest) and ok
                continue

            if dest.exists():
                dest = _unique_legacy_copy_path(dest)
            shutil.copy2(str(child), str(dest))
        except Exception:
            ok = False
    return ok


def _migrate_legacy_appdata_dirs(root: Path, out: Path) -> None:
    global _APPDATA_DIRS_MIGRATED
    if _APPDATA_DIRS_MIGRATED:
        return

    legacy_parent = root / LEGACY_APP_ORGANIZATION
    legacy_candidates = [
        legacy_parent / LEGACY_APP_NAME,
        legacy_parent / APP_NAME,
    ]
    out.mkdir(parents=True, exist_ok=True)

    for legacy in legacy_candidates:
        if not legacy.exists() or not legacy.is_dir() or _paths_same(legacy, out):
            continue
        if _merge_directory_contents(legacy, out):
            try:
                shutil.rmtree(str(legacy))
            except Exception:
                pass

    try:
        if legacy_parent.exists() and legacy_parent.is_dir() and not any(legacy_parent.iterdir()):
            legacy_parent.rmdir()
    except Exception:
        pass

    _APPDATA_DIRS_MIGRATED = True


def _appdata_runtime_dir() -> Path:
    base = os.getenv("APPDATA")
    if base:
        root = Path(base)
    else:
        root = Path.home() / "AppData" / "Roaming"
    out = root / APP_NAME
    _migrate_legacy_appdata_dirs(root, out)
    return out


def _debugging_logs_dir(appdata_dir: Path | None = None) -> Path:
    root = appdata_dir or _appdata_runtime_dir()
    out = root / "debugging-logs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _crash_reports_dir(appdata_dir: Path | None = None) -> Path:
    out = _debugging_logs_dir(appdata_dir) / "crash-reports"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _migrate_legacy_debugging_logs(appdata_dir: Path | None = None) -> None:
    root = appdata_dir or _appdata_runtime_dir()
    debug_dir = _debugging_logs_dir(root)

    def _unique_target(path: Path) -> Path:
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        for idx in range(1, 1000):
            candidate = path.with_name(f"{stem}-{idx}{suffix}")
            if not candidate.exists():
                return candidate
        return path.with_name(f"{stem}-{int(time.time())}{suffix}")

    for name in ("app.log", "faulthandler.log"):
        old_path = root / name
        new_path = debug_dir / name
        if not old_path.exists():
            continue
        try:
            if new_path.exists():
                with open(new_path, "a", encoding="utf-8", errors="replace") as out_handle:
                    out_handle.write("\n")
                    out_handle.write(old_path.read_text(encoding="utf-8", errors="replace"))
                old_path.unlink(missing_ok=True)
            else:
                shutil.move(str(old_path), str(new_path))
        except Exception:
            pass

    old_crash_dir = root / "crash-reports"
    new_crash_dir = debug_dir / "crash-reports"
    if old_crash_dir.exists() and old_crash_dir.is_dir():
        try:
            new_crash_dir.mkdir(parents=True, exist_ok=True)
            for child in old_crash_dir.iterdir():
                target = _unique_target(new_crash_dir / child.name)
                try:
                    shutil.move(str(child), str(target))
                except Exception:
                    pass
            try:
                old_crash_dir.rmdir()
            except Exception:
                pass
        except Exception:
            pass


_WINDOWS_PATH_RE = re.compile(
    r"(?P<path>(?:[A-Za-z]:\\|\\\\)[^\s\"'<>|]+(?:[^\s\"'<>|.,;:)\]}]))"
)
_FILE_URL_RE = re.compile(r"file:///[^\s\"'<>]+")


def _sanitize_diagnostic_text(text: object) -> str:
    raw = str(text)
    raw = _FILE_URL_RE.sub("file:///[redacted-path]", raw)

    def _replace_path(match: re.Match) -> str:
        path_text = match.group("path")
        suffix = Path(path_text).suffix
        if suffix:
            return f"[redacted-path]{suffix}"
        return "[redacted-path]"

    return _WINDOWS_PATH_RE.sub(_replace_path, raw)


def _diagnostic_log_should_write(message: str, *, verbose: bool = False) -> bool:
    if verbose:
        return True
    text = str(message or "").strip()
    if not text:
        return False
    lower = text.lower()
    always_keep = (
        "bridge: initializing",
        "webengine runtime:",
        "dpi:",
        "using ffmpeg",
        "using ffprobe",
        "diagnostic",
    )
    if any(token in lower for token in always_keep):
        return True
    problem_tokens = (
        "error",
        "failed",
        "failure",
        "exception",
        "traceback",
        "crash",
        "invalid",
        "unavailable",
        "missing",
        "rejected",
        "terminated",
        "warning",
        "could not",
        "unable",
    )
    return any(token in lower for token in problem_tokens)


def _runtime_db_path(appdata_dir: Path | None = None) -> Path:
    root = appdata_dir or _appdata_runtime_dir()
    legacy = root / "mediamanagerx.db"
    current = root / "medialens.db"
    if not current.exists() and legacy.exists():
        try:
            shutil.move(str(legacy), str(current))
        except Exception:
            try:
                shutil.copy2(str(legacy), str(current))
            except Exception:
                pass
    return current


def app_settings() -> QSettings:
    global _SETTINGS_MIGRATED
    settings_path = _appdata_runtime_dir() / "settings.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    if _SETTINGS_MIGRATED:
        return settings

    try:
        migrated = bool(settings.value("app/settings_migrated_from_legacy", False, type=bool))
    except Exception:
        migrated = False
    if migrated:
        _SETTINGS_MIGRATED = True
        return settings

    try:
        legacy_sources = [
            QSettings(LEGACY_APP_ORGANIZATION, APP_NAME),
            QSettings(LEGACY_APP_ORGANIZATION, LEGACY_APP_NAME),
        ]
        for legacy in legacy_sources:
            for key in legacy.allKeys():
                if not settings.contains(key):
                    settings.setValue(key, legacy.value(key))
        settings.setValue("app/settings_migrated_from_legacy", True)
        settings.sync()
    except Exception:
        pass
    _SETTINGS_MIGRATED = True
    return settings


def _write_crash_report(kind: str, exc_type=None, exc_value=None, exc_tb=None) -> Path | None:
    try:
        report_dir = _crash_reports_dir()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_path = report_dir / f"{kind}-{stamp}.log"
        lines = [
            f"Version: {__version__}",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Python: {sys.version}",
            f"Executable: {_sanitize_diagnostic_text(sys.executable)}",
            f"Frozen: {bool(getattr(sys, 'frozen', False))}",
            f"CWD: {_sanitize_diagnostic_text(os.getcwd())}",
            _sanitize_diagnostic_text(_format_dpi_state()),
        ]
        if exc_type is not None:
            lines.extend([
                "",
                "Traceback:",
                _sanitize_diagnostic_text("".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip()),
            ])
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return report_path
    except Exception:
        return None


def _install_crash_reporting() -> None:
    global _FAULT_HANDLER_STREAM
    try:
        appdata = _appdata_runtime_dir()
        _migrate_legacy_debugging_logs(appdata)
        faulthandler_log = _debugging_logs_dir(appdata) / "faulthandler.log"
        _FAULT_HANDLER_STREAM = open(faulthandler_log, "a", encoding="utf-8")
        faulthandler.enable(_FAULT_HANDLER_STREAM)
    except Exception:
        pass

    def _handle_exception(exc_type, exc_value, exc_tb):
        report = _write_crash_report("python-crash", exc_type, exc_value, exc_tb)
        try:
            print("Unhandled exception:", file=sys.stderr)
            traceback.print_exception(exc_type, exc_value, exc_tb)
            if report:
                print(f"Crash report written to: {report}", file=sys.stderr)
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def _handle_thread_exception(args):
        _handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = _handle_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = _handle_thread_exception


_install_crash_reporting()




__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
