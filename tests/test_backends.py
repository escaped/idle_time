"""Xprintidle / Sway / Windows monitors (mocked subprocess, file, win32)."""
import sys
import types
import builtins
import idle_time
from idle_time import XprintidleIdleMonitor, SwayIdleMonitor, WindowsIdleMonitor


class _Res:
    def __init__(self, returncode=0, stdout=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = b""


def test_xprintidle_init_fails_without_binary(monkeypatch):
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: _Res(1))
    try:
        XprintidleIdleMonitor()
    except AttributeError:
        pass
    else:
        raise AssertionError("expected AttributeError")


def test_xprintidle_returns_milliseconds(monkeypatch):
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: _Res(0, b"  9876\n"))
    # init checks `which`; get checks `xprintidle` output
    m = XprintidleIdleMonitor()
    assert m.get_dbus_idle() == 9876.0


def test_xprintidle_runtime_failure(monkeypatch):
    calls = {"n": 0}

    def fake_run(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Res(0)  # which ok
        return _Res(1)  # xprintidle failed

    monkeypatch.setattr(idle_time.subprocess, "run", fake_run)
    m = XprintidleIdleMonitor()
    try:
        m.get_dbus_idle()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")


def test_xprintidle_invalid_output(monkeypatch):
    seq = [_Res(0), _Res(0, b"not-a-number\n")]
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: seq.pop(0))
    m = XprintidleIdleMonitor()
    try:
        m.get_dbus_idle()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")


def test_xprintidle_empty_output(monkeypatch):
    seq = [_Res(0), _Res(0, b"  \n")]
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: seq.pop(0))
    m = XprintidleIdleMonitor()
    try:
        m.get_dbus_idle()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")


def test_sway_init_fails_without_binary(monkeypatch):
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: _Res(1))
    try:
        SwayIdleMonitor()
    except AttributeError:
        pass
    else:
        raise AssertionError("expected AttributeError")


def test_sway_zero_file_means_zero_idle(tmp_path, monkeypatch):
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: _Res(0))
    m = SwayIdleMonitor.__new__(SwayIdleMonitor)
    m.output_file = str(tmp_path / "idle.txt")
    with open(m.output_file, "w") as f:
        f.write("0")
    assert m.get_dbus_idle() == 0.0


def test_sway_timestamp_converts_to_ms(tmp_path, monkeypatch):
    monkeypatch.setattr(idle_time.subprocess, "run", lambda *a, **k: _Res(0))
    monkeypatch.setattr(idle_time.time, "time", lambda: 2000.0)
    m = SwayIdleMonitor.__new__(SwayIdleMonitor)
    m.output_file = str(tmp_path / "idle.txt")
    with open(m.output_file, "w") as f:
        f.write("1990")  # 10 s ago -> 10000 ms
    assert m.get_dbus_idle() == 10000.0


def test_windows_uses_tick_delta():
    fake = types.ModuleType("win32api")
    fake.GetTickCount = lambda: 100000
    fake.GetLastInputInfo = lambda: 99500
    sys.modules["win32api"] = fake
    try:
        m = WindowsIdleMonitor()
        assert m.get_dbus_idle() == 500.0
    finally:
        sys.modules.pop("win32api", None)


def test_windows_init_fails_without_pywin32():
    assert "win32api" not in sys.modules
    try:
        WindowsIdleMonitor()
    except (ImportError, ModuleNotFoundError):
        pass
    else:
        raise AssertionError("expected ImportError")
