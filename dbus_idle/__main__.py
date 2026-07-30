from . import IdleMonitor
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="dbus-idle",
        description="Get idle time in seconds from DBus")
    parser.add_argument("-d", "--debug", action="store_true", help="Show debug messeges")
    args = parser.parse_args()

    idle_monitor = IdleMonitor(debug=args.debug)
    milliseconds = idle_monitor.get_dbus_idle()
    print(milliseconds)
