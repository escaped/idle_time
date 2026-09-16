"""DBusIdleMonitor: GNOME/Mutter + KDE discovery via jeepney (mocked)."""

import sys
import types

from idle_time import DBusIdleMonitor


def _install_jeepney_fake(services, idle_value=12345):
    """Install fake jeepney modules; return sent messages list."""
    sent = []

    fake_jeepney = types.ModuleType("jeepney")
    fake_io = types.ModuleType("jeepney.io")
    fake_blocking = types.ModuleType("jeepney.io.blocking")

    class DBusAddress:
        def __init__(self, object_path=None, bus_name=None, interface=None):
            self.object_path = object_path
            self.bus_name = bus_name
            self.interface = interface

    def new_method_call(remote_obj, method):
        return (remote_obj, method)

    class FakeReply:
        def __init__(self, body):
            self.body = body

    class FakeConn:
        def send_and_get_reply(self, msg):
            sent.append(msg)
            _addr, method = msg
            if method == "ListNames":
                return FakeReply([[*services]])
            return FakeReply([idle_value])

    def open_dbus_connection(bus="SESSION"):
        assert bus == "SESSION"
        return FakeConn()

    fake_jeepney.DBusAddress = DBusAddress
    fake_jeepney.new_method_call = new_method_call
    fake_blocking.open_dbus_connection = open_dbus_connection
    fake_io.blocking = fake_blocking
    fake_jeepney.io = fake_io
    sys.modules["jeepney"] = fake_jeepney
    sys.modules["jeepney.io"] = fake_io
    sys.modules["jeepney.io.blocking"] = fake_blocking
    return sent


def _clear_jeepney_fake():
    for m in ["jeepney", "jeepney.io", "jeepney.io.blocking"]:
        sys.modules.pop(m, None)


def test_discovers_gnome_mutterm_idle_monitor():
    _install_jeepney_fake(["org.freedesktop.DBus", "org.gnome.Mutter.IdleMonitor"])
    try:
        m = DBusIdleMonitor()
        assert m.get_dbus_idle() == 12345.0
        addr, method = m.idle_msg
        assert method == "GetIdletime"
        assert addr.bus_name == "org.gnome.Mutter.IdleMonitor"
        assert addr.object_path == "/org/gnome/Mutter/IdleMonitor/Core"
    finally:
        _clear_jeepney_fake()


def test_discovers_generic_idle_monitor_service():
    # PR #8 core: any service containing "IdleMonitor" (other distros/DEs)
    _install_jeepney_fake(["org.freedesktop.DBus", "org.foo.IdleMonitor"])
    try:
        m = DBusIdleMonitor()
        addr, method = m.idle_msg
        assert method == "GetIdletime"
        assert addr.object_path == "/org/foo/IdleMonitor/Core"
        assert m.get_dbus_idle() == 12345.0
    finally:
        _clear_jeepney_fake()


def test_discovers_kde_idletime():
    _install_jeepney_fake(["org.freedesktop.DBus", "org.kde.IdleTime"], idle_value=777)
    try:
        m = DBusIdleMonitor()
        addr, method = m.idle_msg
        assert method == "getIdleTime"
        assert addr.object_path == "/org/kde/IdleTime"
        assert m.get_dbus_idle() == 777.0
    finally:
        _clear_jeepney_fake()


def test_no_idle_service_raises():
    _install_jeepney_fake(["org.freedesktop.DBus", "org.foo.Bar"])
    try:
        try:
            DBusIdleMonitor()
        except AttributeError:
            pass
        else:
            raise AssertionError("expected AttributeError")
    finally:
        _clear_jeepney_fake()


def test_dbus_connection_failure_propagates():
    fake = types.ModuleType("jeepney")
    fake.DBusAddress = object
    fake.new_method_call = lambda *a, **k: None
    io = types.ModuleType("jeepney.io")
    blk = types.ModuleType("jeepney.io.blocking")

    def boom(bus="SESSION"):
        raise ConnectionError("no bus")

    blk.open_dbus_connection = boom
    io.blocking = blk
    fake.io = io
    sys.modules["jeepney"] = fake
    sys.modules["jeepney.io"] = io
    sys.modules["jeepney.io.blocking"] = blk
    try:
        try:
            DBusIdleMonitor()
        except ConnectionError:
            pass
        else:
            raise AssertionError("expected ConnectionError")
    finally:
        _clear_jeepney_fake()
