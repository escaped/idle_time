from . import IdleMonitor
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="dbus-idle",
        description="Get idle time in seconds from DBus")
    parser.parse_args()

    milliseconds = IdleMonitor().get_dbus_idle()
    print(milliseconds)
