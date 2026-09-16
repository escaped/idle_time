"""X11IdleMonitor with faked ctypes libs (no display needed)."""
import ctypes
import idle_time
from idle_time import X11IdleMonitor


class _IdleContents:
    def __init__(self, idle):
        self.idle = idle


class _FakePtr:
    def __init__(self, idle):
        self.contents = _IdleContents(idle)


def _make_x11(display=0x1):
    # instance attributes (not bound methods) so production code can set
    # .argtypes/.restype on them like real ctypes functions.
    class NS:
        pass

    ns = NS()
    ns.XOpenDisplay = lambda arg=None: display
    ns.XDefaultRootWindow = lambda d: 42
    ns.closed = []
    ns.XCloseDisplay = lambda d: ns.closed.append(d) or 0
    return ns


def _make_xss(idle=321, status=1):
    class NS:
        pass

    ns = NS()
    state = {"status": status, "idle": idle, "calls": 0}

    def alloc():
        return _FakePtr(state["idle"])

    def query(display, root, info):
        state["calls"] += 1
        return state["status"]

    ns.XScreenSaverAllocInfo = alloc
    ns.XScreenSaverQueryInfo = query
    ns._state = state
    return ns


def _patch(monkeypatch, x11=None, xss=None, find_ok=True):
    x11 = x11 if x11 is not None else _make_x11()
    xss = xss if xss is not None else _make_xss()

    def fake_find(name):
        if not find_ok:
            return None
        return f"/lib/lib{name}.so"

    def fake_load(path):
        return x11 if "X11" in path else xss

    monkeypatch.setattr(idle_time.ctypes.util, "find_library", fake_find)
    monkeypatch.setattr(idle_time.ctypes.cdll, "LoadLibrary", fake_load)
    return x11, xss


def test_x11_returns_idle_ms(monkeypatch):
    _patch(monkeypatch, xss=_make_xss(idle=321))
    m = X11IdleMonitor()
    assert m.get_dbus_idle() == 321.0


def test_x11_no_display_raises(monkeypatch):
    _patch(monkeypatch, x11=_make_x11(display=None))
    try:
        X11IdleMonitor()
    except AttributeError:
        pass
    else:
        raise AssertionError("expected AttributeError")


def test_x11_missing_lib_raises(monkeypatch):
    _patch(monkeypatch, find_ok=False)
    try:
        X11IdleMonitor()
    except OSError:
        pass
    else:
        raise AssertionError("expected OSError")


def test_x11_unsupported_status_raises_and_closes(monkeypatch):
    x11, _ = _patch(monkeypatch, xss=_make_xss(status=0))
    try:
        X11IdleMonitor()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
    assert x11.closed, "display must be closed on failed init"


def test_x11_query_failure_at_call_time(monkeypatch):
    x11, xss = _patch(monkeypatch, xss=_make_xss(idle=5, status=1))
    m = X11IdleMonitor()
    xss._state["status"] = 0
    try:
        m.get_dbus_idle()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
