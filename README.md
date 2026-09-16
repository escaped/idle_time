# idle-time

[![pypi](https://img.shields.io/pypi/v/idle-time.svg)](https://pypi.python.org/pypi/idle-time)
![python version](https://img.shields.io/pypi/pyversions/idle-time.svg)
![license](https://img.shields.io/pypi/l/idle-time.svg)

Python library to detect user idle time in milliseconds or inactivity on Linux and Windows.


## Requirements

* Python 3.7 or later


## Installation

Install using:
```
pip install idle-time
```


## Usage

You can use this module from the command line
```bash
idle-time
```
or access the current idle time from within your python program
```python
from idle_time import IdleMonitor

milliseconds = IdleMonitor().get_dbus_idle()
```

## Supported backends

`IdleMonitor()` automatically picks the first working backend, in this order:

| Backend | Environment | Notes |
|---|---|---|
| `DBusIdleMonitor` | Linux desktops on DBus (GNOME, KDE Plasma, ...) | Discovers any `*IdleMonitor*` service on the session bus; falls back to `org.kde.IdleTime`. |
| `XprintidleIdleMonitor` | Linux / X11 | Requires the `xprintidle` binary. |
| `X11IdleMonitor` | Linux / X11 | Uses `XScreenSaverQueryInfo` (libX11 + libXss). |
| `SwayIdleMonitor` | Linux / Wayland (sway) | Requires the `swayidle` binary; writes to `/tmp/idletime.txt`. |
| `WindowsIdleMonitor` | Windows | Requires `pywin32`. |

`get_dbus_idle()` returns the idle time in **milliseconds**, or `None` if no
backend is available. `is_idle()` compares against `idle_threshold`
(default `120`) — note the threshold is currently compared against
milliseconds.
