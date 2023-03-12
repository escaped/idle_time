from . import IdleMonitor
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="dbus-idle",
        description="Get idle time in seconds from DBus")
    parser.parse_args()

    monitor = IdleMonitor.get_monitor()
    print(monitor.get_dbus_idle())
