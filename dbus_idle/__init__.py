import time
import ctypes
import ctypes.util
import logging
from typing import Any, List, Type
import subprocess


logger = logging.getLogger("dbus_idle")
logging.basicConfig(level=logging.ERROR)

class IdleMonitor:
    subclasses: List[Type["IdleMonitor"]] = []

    def __init__(self, *, idle_threshold: int = 120, debug: bool=False) -> None:
        self.idle_threshold = idle_threshold
        self.class_used = None
        if debug:
            logger.setLevel(logging.DEBUG)

    def __init_subclass__(self) -> None:
        super().__init_subclass__()
        self.subclasses.append(self)

    @classmethod
    def get_monitor(self, **kwargs) -> "IdleMonitor":
        """
        Return the first available idle monitor.
        """
        for monitor_class in self.subclasses:
            try:
                return monitor_class(**kwargs)
            except Exception:
                logger.warning("Could not load %s", monitor_class, exc_info=True)
        raise RuntimeError("Could not find a working monitor.")

    def get_dbus_idle(self) -> float:
        """
        Return idle time in milliseconds.
        """
        if self.class_used is None:
            for monitor_class in self.subclasses:
                try:
                    self.class_used = monitor_class()
                    logger.debug("Using: %s", monitor_class.__name__)
                    return self.class_used.get_dbus_idle()
                except Exception:
                    logger.info("Could not load %s", monitor_class.__name__, exc_info=False)
                    self.class_used = None
            logger.warning("Could not find any working monitor to get idle time.", exc_info=True)
            return None
        else:
            try:
                return self.class_used.get_dbus_idle()
            except Exception as e:
                logger.warning("Can't run the working monitor anymore.", exc_info=False)
                self.class_used = None
                return None

    def is_idle(self) -> bool:
        """
        Return whether the user is idling.
        """
        idle_time = self.get_dbus_idle()
        if idle_time is None:
            return False
        return idle_time > self.idle_threshold


class DBusIdleMonitor(IdleMonitor):
    """
    Idle monitor for Linux desktop environments (GNOME, KDE Plasma, etc.) running on DBus.

    Based on
      * https://unix.stackexchange.com/a/492328
    """

    def __init__(self, **kwargs) -> None:
        from jeepney import DBusAddress, new_method_call
        from jeepney.io.blocking import open_dbus_connection

        self.connection = open_dbus_connection(bus="SESSION")
        dbus_addr = DBusAddress(
            object_path="/org/freedesktop/DBus",
            bus_name="org.freedesktop.DBus",
            interface="org.freedesktop.DBus",
        )

        msg = new_method_call(remote_obj=dbus_addr, method="ListNames")
        reply = self.connection.send_and_get_reply(msg)
        self.idle_msg = None
        for service in reply.body[0]:
            if "IdleMonitor" in service:
                service_path = f"/{service.replace('.', '/')}/Core"
                idle_addr = DBusAddress(service_path, bus_name=service, interface=service)
                self.idle_msg = new_method_call(remote_obj=idle_addr, method="GetIdletime")
                break
            elif "org.kde.IdleTime" in service or service == "org.kde.IdleTime":
                idle_addr = DBusAddress("/org/kde/IdleTime", bus_name=service, interface="org.kde.IdleTime")
                self.idle_msg = new_method_call(remote_obj=idle_addr, method="getIdleTime")
                break
        if self.idle_msg is None:
            raise AttributeError()

    def get_dbus_idle(self) -> float:
        idle_reply = self.connection.send_and_get_reply(self.idle_msg)
        return float(idle_reply.body[0])


class XprintidleIdleMonitor(IdleMonitor):
    """Idle monitor using xprintidle command."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        command = subprocess.run(
            ["which", "xprintidle"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        if command.returncode != 0:
            raise AttributeError()

    def get_dbus_idle(self) -> float:
        res = subprocess.run(
            'xprintidle',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError("xprintidle failed")
        stdout = res.stdout.decode("UTF-8").strip()
        if not stdout or not stdout.isdigit():
            raise RuntimeError("xprintidle output invalid")

        idle_sec = int(stdout)
        return float(idle_sec)


class X11IdleMonitor(IdleMonitor):
    """
    Idle monitor for systems running X11.

    Based on
      * http://tperl.blogspot.com/2007/09/x11-idle-time-and-focused-window-in.html
      * https://stackoverflow.com/a/55966565/7774036
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        class XScreenSaverInfo(ctypes.Structure):
            _fields_ = [
                ("window", ctypes.c_ulong),  # screen saver window
                ("state", ctypes.c_int),  # off, on, disabled
                ("kind", ctypes.c_int),  # blanked, internal, external
                ("since", ctypes.c_ulong),  # milliseconds
                ("idle", ctypes.c_ulong),  # milliseconds
                ("event_mask", ctypes.c_ulong),
            ]  # events

        self.lib_x11 = self._load_lib("X11")
        # specify required types
        self.lib_x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.lib_x11.XOpenDisplay.restype = ctypes.c_void_p
        self.lib_x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.lib_x11.XDefaultRootWindow.restype = ctypes.c_uint32
        self.lib_x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.lib_x11.XCloseDisplay.restype = ctypes.c_int

        self.display = self.lib_x11.XOpenDisplay(None)
        if self.display is None:
            raise AttributeError()

        try:
            self.root_window = self.lib_x11.XDefaultRootWindow(self.display)

            self.lib_xss = self._load_lib("Xss")
            # specify required types
            self.lib_xss.XScreenSaverQueryInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.POINTER(XScreenSaverInfo),
            ]
            self.lib_xss.XScreenSaverQueryInfo.restype = ctypes.c_int
            self.lib_xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
            # allocate memory for idle information
            self.xss_info = self.lib_xss.XScreenSaverAllocInfo()

            status = self.lib_xss.XScreenSaverQueryInfo(self.display, self.root_window, self.xss_info)
            if status == 0:
                raise RuntimeError("Not Supported...")
        except Exception:
            if getattr(self, "display", None) and getattr(self, "lib_x11", None):
                try:
                    self.lib_x11.XCloseDisplay(self.display)
                except Exception:
                    pass
                self.display = None
            raise

    def get_dbus_idle(self) -> float:
        status = self.lib_xss.XScreenSaverQueryInfo(self.display, self.root_window, self.xss_info)
        if status == 0:
            raise RuntimeError("XScreenSaverQueryInfo failed")
        return float(self.xss_info.contents.idle)

    def _load_lib(self, name: str) -> Any:
        path = ctypes.util.find_library(name)
        if path is None:
            raise OSError(f"Could not find library `{name}`")
        return ctypes.cdll.LoadLibrary(path)

    def __del__(self) -> None:
        if getattr(self, "display", None) and getattr(self, "lib_x11", None):
            try:
                self.lib_x11.XCloseDisplay(self.display)
                self.display = None
            except Exception:
                pass


class SwayIdleMonitor(IdleMonitor):
    """Idle monitor using swayidle command for Wayland environments."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.output_file = "/tmp/idletime.txt"
        command = subprocess.run(
            ["which", "swayidle"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        if command.returncode != 0:
            raise AttributeError()
        with open(self.output_file, "w") as file:
            file.write("0")
        subprocess.run(
            f'swayidle -w timeout 1 "echo -n \\$(date +%s) > {self.output_file}" resume "echo -n 0 > {self.output_file}" &',
            shell=True,
        )

    def get_dbus_idle(self) -> float:
        with open(self.output_file, "r") as file:
            idle_time = int(file.read())
            if idle_time != 0:
                idle_time = time.time() - idle_time

        return idle_time * 1000


class WindowsIdleMonitor(IdleMonitor):
    """
    Idle monitor for Windows.

    Based on
      * https://stackoverflow.com/q/911856
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        import win32api
        self.win32api = win32api

    def get_dbus_idle(self) -> float:
        current_tick = self.win32api.GetTickCount()
        last_tick = self.win32api.GetLastInputInfo()
        return float(current_tick - last_tick)
