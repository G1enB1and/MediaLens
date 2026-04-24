from __future__ import annotations

from native.mediamanagerx_app.common import *
from native.mediamanagerx_app.runtime_paths import *
from native.mediamanagerx_app.theme_dialogs import *
from native.mediamanagerx_app.window import *

def _create_startup_splash(app: QApplication, startup_bg: QColor) -> QSplashScreen | None:
    try:
        splash_path = Path(__file__).with_name("web") / "MediaLens-Logo-1024.png"
        if not splash_path.exists():
            return None
        source = QPixmap(str(splash_path))
        if source.isNull():
            return None

        screen = app.primaryScreen()
        target_w = 1024
        target_h = 1024
        if screen is not None:
            available = screen.availableGeometry().size()
            max_w = max(320, min(target_w, int(available.width() * 0.8)))
            max_h = max(320, min(target_h, int(available.height() * 0.8)))
        else:
            max_w = target_w
            max_h = target_h

        scaled = source.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        splash_pixmap = QPixmap(scaled.size())
        splash_pixmap.fill(Qt.GlobalColor.transparent)
        splash_pixmap.setDevicePixelRatio(scaled.devicePixelRatio())
        painter = QPainter(splash_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        splash = QSplashScreen(splash_pixmap)
        splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        return splash
    except Exception:
        return None


def _remote_version_is_newer(remote_version: str) -> bool:
    try:
        return bool(remote_version) and Version(str(remote_version).strip()) > Version(__version__)
    except Exception:
        return False


def _fetch_latest_version_for_startup(timeout_seconds: float = 6.0) -> str:
    request = urllib.request.Request(
        UPDATE_VERSION_URL,
        headers={"User-Agent": f"MediaLens/{__version__}"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read(128).decode("utf-8", errors="replace").strip()


def _download_update_installer_with_dialog(app: QApplication, version: str) -> Path | None:
    temp_dir = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation) or tempfile.gettempdir())
    temp_dir.mkdir(parents=True, exist_ok=True)
    setup_path = temp_dir / "MediaLens_Setup_New.exe"
    progress = QProgressDialog(f"Downloading MediaLens {version}...", "Cancel", 0, 100)
    progress.setWindowTitle("Downloading Update")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)
    progress.show()
    app.processEvents()
    try:
        request = urllib.request.Request(
            UPDATE_INSTALLER_URL,
            headers={"User-Agent": f"MediaLens/{__version__}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            total = int(response.headers.get("Content-Length") or 0)
            received = 0
            with open(setup_path, "wb") as handle:
                while True:
                    if progress.wasCanceled():
                        return None
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
                    received += len(chunk)
                    if total > 0:
                        progress.setValue(max(0, min(100, int((received / total) * 100))))
                    else:
                        progress.setLabelText(f"Downloading MediaLens {version}...\n{received // 1024} KB")
                    app.processEvents()
        progress.setValue(100)
        return setup_path
    finally:
        progress.close()


def _launch_update_installer(setup_path: Path) -> None:
    subprocess.Popen([str(setup_path), "/SILENT", "/SP-", "/NOICONS", "/RELAUNCH"])


def _run_startup_update_check(app: QApplication, settings: QSettings) -> bool:
    if not bool(settings.value("updates/check_on_launch", True, type=bool)):
        return False
    try:
        remote_version = _fetch_latest_version_for_startup()
    except Exception:
        return False
    if not _remote_version_is_newer(remote_version):
        return False

    answer = QMessageBox.question(
        None,
        "Update Available",
        (
            f"MediaLens {remote_version} is available.\n\n"
            f"You are currently using {__version__}.\n\n"
            "Download and install the update before opening MediaLens?"
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return False

    try:
        setup_path = _download_update_installer_with_dialog(app, remote_version)
        if setup_path is None:
            return False
        _launch_update_installer(setup_path)
        return True
    except Exception as exc:
        QMessageBox.warning(
            None,
            "Update Error",
            f"Unable to download or launch the update installer:\n{exc}",
        )
        return False


def main() -> None:
    if os.name == "nt" and bool(_WINDOWS_WEBENGINE_RUNTIME.get("enabled")):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    app = QApplication(sys.argv)
    app.setStyle(ToolTipProxyStyle(app.style()))

    # Keep the visible Qt app name aligned with the installed product name.
    app.setOrganizationName(APP_NAME)
    app.setApplicationName(APP_NAME)

    startup_settings = app_settings()
    startup_theme = str(startup_settings.value("ui/theme_mode", "dark", type=str) or "dark")
    startup_accent = str(startup_settings.value("ui/accent_color", Theme.ACCENT_DEFAULT, type=str) or Theme.ACCENT_DEFAULT)
    show_splash = bool(startup_settings.value("ui/show_splash_screen", True, type=bool))
    Theme.set_theme_mode(startup_theme)
    startup_bg = QColor(Theme.get_bg(QColor(startup_accent)))
    startup_fg = QColor(Theme.get_text_color())
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, startup_bg)
    palette.setColor(QPalette.ColorRole.Base, startup_bg)
    palette.setColor(QPalette.ColorRole.Button, startup_bg)
    palette.setColor(QPalette.ColorRole.WindowText, startup_fg)
    palette.setColor(QPalette.ColorRole.Text, startup_fg)
    app.setPalette(palette)
    tooltip_palette = app.palette()
    tooltip_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Theme.get_bg(QColor(startup_accent))))
    tooltip_palette.setColor(QPalette.ColorRole.ToolTipText, startup_fg)
    QToolTip.setPalette(tooltip_palette)
    app.setStyleSheet(
        f"""
        QWidget {{ background-color: {startup_bg.name()}; color: {startup_fg.name()}; }}
        QToolTip {{
            background-color: {Theme.get_input_bg(QColor(startup_accent))};
            color: {startup_fg.name()};
            border: 1px solid {Theme.get_input_border(QColor(startup_accent))};
            padding: 4px 6px;
        }}
        """
    )

    if _run_startup_update_check(app, startup_settings):
        sys.exit(0)

    splash = _create_startup_splash(app, startup_bg) if show_splash else None
    if splash is not None:
        splash.show()
        app.processEvents()

    win = MainWindow()
    try:
        _log_dpi_state(app, win.bridge._log)
    except Exception:
        pass

    def _mark_bridge_shutting_down() -> None:
        try:
            win.bridge._shutting_down = True
            win.bridge._scan_abort = True
            win.bridge._local_ai_shutting_down = True
        except Exception:
            pass
    app.aboutToQuit.connect(_mark_bridge_shutting_down)

    splash_closed = False

    def _finish_splash() -> None:
        nonlocal splash_closed
        if splash is None or splash_closed:
            return
        splash_closed = True
        if win.isVisible():
            splash.finish(win)
        else:
            splash.close()

    if splash is not None:
        try:
            win.web.loadFinished.connect(lambda _ok: _finish_splash())
        except Exception:
            pass
        QTimer.singleShot(4000, _finish_splash)

    win.show()
    QTimer.singleShot(900, win.maybe_show_local_ai_setup_onboarding)

    if splash is None:
        pass
    elif win.web is None:
        _finish_splash()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()



__all__ = [name for name in globals() if name == "__version__" or not (name.startswith("__") and name.endswith("__"))]
