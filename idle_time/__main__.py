from . import IdleMonitor
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="idle-time",
        description="Get idle time in milliseconds")
    parser.add_argument("-d", "--debug", action="store_true", help="Show debug messeges")
    args = parser.parse_args()

    idle_monitor = IdleMonitor(debug=args.debug)
    milliseconds = idle_monitor.get_dbus_idle()
    print(milliseconds)


if __name__ == "__main__":
    main()
