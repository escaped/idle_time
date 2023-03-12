# dbus-idle

[![pypi](https://img.shields.io/pypi/v/dbus-idle.svg)](https://pypi.python.org/pypi/dbus-idle)
![python version](https://img.shields.io/pypi/pyversions/dbus-idle.svg)
![Project status](https://img.shields.io/pypi/status/dbus-idle.svg)
![license](https://img.shields.io/pypi/l/dbus-idle.svg)


Detect user idle time or inactivity on Linux and Windows.


## Requirements

* Python 3.7 or later


## Installation

Install using `pip install dbus-idle`


## Usage

You can use this module from the command line

    python -m dbus-idle

or access the current idle time from within your python program


    from dbus_idle import IdleMonitor

    monitor = IdleMonitor.get_monitor()
    monitor.get_dbus_idle()

## Contribution
This is based on the work by [Alexander Frenzel](https://github.com/escaped/dbus_idle)
