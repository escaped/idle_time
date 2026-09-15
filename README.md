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
