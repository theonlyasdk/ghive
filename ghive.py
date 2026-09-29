#!/usr/bin/env python3
"""ghive - GUI frontend for GitHub CLI.

Main entry point for the application.
Automatically verifies dependencies, handles high-DPI scaling, and starts the UI.
"""

import os
import signal
import sys
import time
from pathlib import Path

# Enable high DPI awareness on Windows
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import DependencyManager
from ui import InitDialog, MainWindow

current_app = None
last_ctrl_c = 0.0


def handle_ctrl_c():
    """Handle Ctrl+C interrupts: require double-press to exit."""
    global last_ctrl_c
    now = time.time()
    if now - last_ctrl_c <= 4.0:
        print("\nExiting ghive...", flush=True)
        try:
            if current_app and getattr(current_app, "root", None):
                current_app.root.destroy()
        except Exception:
            pass
        os._exit(0)
    else:
        last_ctrl_c = now
        print("\nPress ctrl+c again to exit ghive...", flush=True)


# Register native Windows Console Ctrl Handler so Ctrl+C in console works immediately
_win_handler_ref = None
if sys.platform == "win32":
    try:
        import ctypes
        import ctypes.wintypes

        @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.DWORD)
        def _win_console_ctrl_handler(event_type):
            if event_type in (0, 1):  # 0: CTRL_C_EVENT, 1: CTRL_BREAK_EVENT
                handle_ctrl_c()
                return True
            return False

        _win_handler_ref = _win_console_ctrl_handler
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_win_handler_ref, True)
    except Exception:
        pass


def sigint_handler(signum, frame):
    """Handle POSIX SIGINT signal."""
    handle_ctrl_c()


def main():
    """Main application lifecycle entry point."""
    global current_app
    print("Starting ghive...")
    print("Checking dependencies...")

    dep_manager = DependencyManager()
    gh_path = None
    show_dialog = False

    try:
        gh_path = dep_manager.get_gh_path()
        ver = dep_manager.get_gh_version(gh_path)
        print(f"✓ GitHub CLI found at: {gh_path} ({ver})")
    except Exception:
        print("✗ GitHub CLI not found")
        show_dialog = True

    if show_dialog:
        print("Initializing dependency configuration...")
        init_dialog = InitDialog()
        current_app = init_dialog
        success, gh_path = init_dialog.run()

        if not success or not gh_path:
            print("Initialization cancelled or missing GitHub CLI. Exiting.")
            return

    print("Launching UI...")
    app = MainWindow(gh_path)
    current_app = app
    app.run()



if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, sigint_handler)
    except Exception:
        pass

    try:
        main()
    except KeyboardInterrupt:
        handle_ctrl_c()

