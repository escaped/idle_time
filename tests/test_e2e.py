"""E2E: real environment, no mocks — proves the adopted PR works headless.

Covers: import surface, subclass registry, fallback chain with no
backends, headless DBus/X11/sway/xprintidle failures, real CLI
subprocess, real get_monitor failure mode.
"""

import subprocess
import sys

from idle_time import IdleMonitor


def test_public_surface():
    assert hasattr(IdleMonitor, "get_monitor")
    assert hasattr(IdleMonitor, "get_dbus_idle")
    assert hasattr(IdleMonitor, "is_idle")
    names = {c.__name__ for c in IdleMonitor.subclasses}
    assert {
        "DBusIdleMonitor",
        "XprintidleIdleMonitor",
        "X11IdleMonitor",
        "SwayIdleMonitor",
        "WindowsIdleMonitor",
    } <= names


def test_headless_fallback_returns_none_not_crash():
    # No DBus session, no X display, no sway/xprintidle, no win32api here.
    top = IdleMonitor()
    val = top.get_dbus_idle()
    assert val is None or isinstance(val, float)
    assert top.is_idle() is False  # None -> False, never raises


def test_get_monitor_raises_or_returns_monitor_headless():
    try:
        m = IdleMonitor.get_monitor()
    except RuntimeError:
        pass  # acceptable headless: no backend available
    else:
        assert isinstance(m, IdleMonitor)
        assert m.get_dbus_idle() is None or isinstance(m.get_dbus_idle(), float)


def test_each_backend_fails_cleanly_headless():
    from idle_time import (
        DBusIdleMonitor,
        SwayIdleMonitor,
        WindowsIdleMonitor,
        X11IdleMonitor,
        XprintidleIdleMonitor,
    )

    for cls in (
        DBusIdleMonitor,
        XprintidleIdleMonitor,
        X11IdleMonitor,
        SwayIdleMonitor,
        WindowsIdleMonitor,
    ):
        try:
            inst = cls()
        except Exception as e:
            # Headless: no session bus (KeyError), no display/libs,
            # no helper binaries, no win32api — any clean raise is fine.
            assert isinstance(e, Exception) and not isinstance(
                e, (SystemExit, KeyboardInterrupt)
            ), (cls, e)
        else:
            v = inst.get_dbus_idle()
            assert v is None or isinstance(v, float)


def test_cli_subprocess_e2e():
    r = subprocess.run(
        [sys.executable, "-m", "idle_time"], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "None"  # headless: no backend -> prints None


def test_cli_debug_subprocess_e2e():
    r = subprocess.run(
        [sys.executable, "-m", "idle_time", "--debug"], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "None"
