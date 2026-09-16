"""CLI (__main__.main) tests."""
import idle_time.__main__ as cli
from idle_time import IdleMonitor


def test_cli_prints_idle(monkeypatch, capsys):
    monkeypatch.setattr(IdleMonitor, "get_dbus_idle", lambda self: 4242.0)
    monkeypatch.setattr("sys.argv", ["idle-time"])
    cli.main()
    out = capsys.readouterr().out.strip()
    assert out == "4242.0"


def test_cli_debug_flag(monkeypatch, capsys):
    import logging
    seen = {}

    orig_init = IdleMonitor.__init__

    def spy_init(self, **kw):
        seen.update(kw)
        orig_init(self, **kw)

    monkeypatch.setattr(IdleMonitor, "__init__", spy_init)
    monkeypatch.setattr(IdleMonitor, "get_dbus_idle", lambda self: 1.0)
    monkeypatch.setattr("sys.argv", ["idle-time", "--debug"])
    cli.main()
    assert seen.get("debug") is True
    logging.getLogger("idle_time").setLevel(logging.ERROR)
