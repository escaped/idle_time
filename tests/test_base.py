"""Base IdleMonitor dispatcher: get_monitor / get_dbus_idle / is_idle."""
import logging
import idle_time
from idle_time import IdleMonitor


class _Good(IdleMonitor):
    def get_dbus_idle(self):
        return 5000.0


class _Bad(IdleMonitor):
    def __init__(self, **kwargs):
        raise RuntimeError("no backend")


def test_subclass_registration():
    assert _Good in IdleMonitor.subclasses
    assert _Bad in IdleMonitor.subclasses


def test_get_monitor_returns_first_working():
    m = IdleMonitor.get_monitor()
    assert isinstance(m, IdleMonitor)


def test_get_monitor_skips_failing():
    # _Bad raises; registry order is definition order in idle_time + locals.
    # Force registry to [bad, good] to prove skip logic.
    IdleMonitor.subclasses[:] = [_Bad, _Good]
    m = IdleMonitor.get_monitor()
    assert isinstance(m, _Good)


def test_get_monitor_raises_when_all_fail():
    IdleMonitor.subclasses[:] = [_Bad]
    try:
        IdleMonitor.get_monitor()
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")


def test_dispatcher_uses_first_working_subclass_and_caches():
    calls = []

    class BackendA(IdleMonitor):
        def get_dbus_idle(self):
            calls.append("A")
            return 111.0

    class BackendB(IdleMonitor):
        def get_dbus_idle(self):
            calls.append("B")
            return 222.0

    IdleMonitor.subclasses[:] = [BackendA, BackendB]
    top = IdleMonitor()
    assert top.get_dbus_idle() == 111.0
    assert isinstance(top.class_used, BackendA)
    # second call reuses cached backend, does not rescan
    assert top.get_dbus_idle() == 111.0
    assert calls == ["A", "A"]


def test_dispatcher_skips_broken_backend():
    class Broken(IdleMonitor):
        def __init__(self, **kw):
            raise AttributeError()

    class Working(IdleMonitor):
        def get_dbus_idle(self):
            return 42.0

    IdleMonitor.subclasses[:] = [Broken, Working]
    assert IdleMonitor().get_dbus_idle() == 42.0


def test_dispatcher_returns_none_when_nothing_works():
    class Broken(IdleMonitor):
        def __init__(self, **kw):
            raise AttributeError()

    IdleMonitor.subclasses[:] = [Broken]
    assert IdleMonitor().get_dbus_idle() is None


def test_cached_backend_failure_resets_to_none():
    class Flaky(IdleMonitor):
        def __init__(self, **kw):
            pass

        def get_dbus_idle(self):
            raise RuntimeError("died")

    IdleMonitor.subclasses[:] = [Flaky]
    top = IdleMonitor()
    top.class_used = Flaky()
    assert top.get_dbus_idle() is None
    assert top.class_used is None


def test_is_idle_threshold():
    IdleMonitor.subclasses[:] = [_Good]  # returns 5000.0
    top = IdleMonitor(idle_threshold=120)
    # 5000 ms > 120 -> idle. Threshold unit is raw ms in PR code.
    assert top.is_idle() is True
    top2 = IdleMonitor(idle_threshold=99999)
    # _Good still returns 5000 -> not idle
    # patch class_used path: force small value
    top2.class_used = _Good()
    _Good.get_dbus_idle = lambda self: 10.0
    assert top2.is_idle() is False


def test_is_idle_none_means_not_idle():
    IdleMonitor.subclasses[:] = []
    assert IdleMonitor().is_idle() is False


def test_debug_flag_sets_debug_level():
    root = logging.getLogger("idle_time")
    old = root.level
    try:
        IdleMonitor(debug=True)
        assert root.level == logging.DEBUG
    finally:
        root.setLevel(old)
