"""Gap-closure tests to reach 100%: X11 cleanup-failure paths,
Sway happy-path init, __main__ guard."""
import runpy
import idle_time
from idle_time import IdleMonitor, X11IdleMonitor, SwayIdleMonitor
from test_x11 import _make_x11, _make_xss, _patch


class _Res:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.stdout = b""
        self.stderr = b""


def test_x11_cleanup_close_raises_still_reraises(monkeypatch):
    x11 = _make_x11()
    x11.XCloseDisplay = lambda d: (_ for _ in ()).throw(OSError("close failed"))
    _patch(monkeypatch, x11=x11, xss=_make_xss(status=0))
    try:
        X11IdleMonitor()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")


def test_x11_del_closes_display(monkeypatch):
    _patch(monkeypatch)
    m = X11IdleMonitor()
    assert m.display is not None
    m.__del__()
    assert m.display is None


def test_x11_del_close_raises_suppressed(monkeypatch):
    _patch(monkeypatch)
    m = X11IdleMonitor()
    m.lib_x11.XCloseDisplay = lambda d: (_ for _ in ()).throw(OSError("x"))
    m.__del__()  # must not raise


def test_x11_del_without_display_ok():
    m = X11IdleMonitor.__new__(X11IdleMonitor)
    m.display = None
    m.lib_x11 = None
    m.__del__()


def test_sway_init_success_writes_file(monkeypatch, tmp_path):
    import builtins
    real_open = builtins.open
    target = tmp_path / "idletime.txt"
    calls = []

    def fake_run(*a, **k):
        calls.append(a)
        return _Res(0)

    def fake_open(path, *a, **k):
        if str(path) == "/tmp/idletime.txt":
            return real_open(target, *a, **k)
        return real_open(path, *a, **k)

    monkeypatch.setattr(idle_time.subprocess, "run", fake_run)
    monkeypatch.setattr(builtins, "open", fake_open)
    m = SwayIdleMonitor()
    assert len(calls) == 2  # which + daemon spawn
    assert target.read_text() == "0"
    # file with 0 -> zero idle
    m.output_file = str(target)
    assert m.get_dbus_idle() == 0.0


def test_main_guard_calls_main(monkeypatch, capsys):
    monkeypatch.setattr(IdleMonitor, "get_dbus_idle", lambda self: 7.0)
    monkeypatch.setattr("sys.argv", ["idle_time"])
    runpy.run_module("idle_time.__main__", run_name="__main__", alter_sys=True)
    assert capsys.readouterr().out.strip() == "7.0"
