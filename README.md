# idle-time

[![pypi](https://img.shields.io/pypi/v/idle-time.svg)](https://pypi.python.org/pypi/idle-time) [![Build Status](https://travis-ci.org/escaped/idle-time.png?branch=master)](http://travis-ci.org/escaped/idle-time) [![Coverage](https://coveralls.io/repos/escaped/idle-time/badge.png?branch=master)](https://coveralls.io/r/escaped/idle-time) ![python version](https://img.shields.io/pypi/pyversions/idle-time.svg) ![Project status](https://img.shields.io/pypi/status/idle-time.svg) ![license](https://img.shields.io/pypi/l/idle-time.svg)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fescaped%2Fidle_time.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2Fescaped%2Fidle_time?ref=badge_shield)

Detect user idle time or inactivity on Linux and Windows.

**WARNING** This project is in an alpha status! Though there is already some code to support Windows, it has only been tested on Wayland/Gnome. 


## Requirements

* Python 3.6 or later


## Installation

Install using `pip install idle-time`


## Usage

You can use this module from the command line

    python -m idle-time

or access the current idle time from within your python program


    from idle_time import IdleMonitor

    monitor = IdleMonitor.get_monitor()
    monitor.get_idle_time()


## License
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2Fescaped%2Fidle_time.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2Fescaped%2Fidle_time?ref=badge_large)