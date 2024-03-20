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
        for monitor_class in self.subclasses:
            try:
                idle_time = monitor_class().get_dbus_idle()
                logger.info("Using: %s", monitor_class.__name__)
                return idle_time
            except Exception:
                logger.warning("Could not load %s", monitor_class.__name__, exc_info=False)
        return None


    def is_idle(self) -> bool:
        """
        Return whether the user is idling.
        """
        return self.get_dbus_idle() > self.idle_threshold


class DBusIdleMonitor(IdleMonitor):
    """
    Idle monitor for gnome running on wayland.

    Based on
      * https://unix.stackexchange.com/a/492328
    """

    def __init__(self, **kwargs) -> None:
        import dbus
        super().__init__(**kwargs)

        session_bus = dbus.SessionBus()
        for service in session_bus.list_names():
            if 'IdleMonitor' in service:
                service_path = f"/{service.replace('.', '/')}/Core"
                self.connection = session_bus.get_object(service, service_path)
                self.service = service
        if not hasattr(self, 'connection'):
            raise AttributeError()

    def get_dbus_idle(self) -> float:
        dbus_idle = self.connection.GetIdletime(dbus_interface=self.service)
        return int(dbus_idle)


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
        stdout = subprocess.run(
            'xprintidle',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).stdout.decode("UTF-8")

        idle_sec = int(stdout.strip())

        return idle_sec


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

        lib_x11 = self._load_lib("X11")
        # specify required types
        lib_x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib_x11.XOpenDisplay.restype = ctypes.c_void_p
        lib_x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        lib_x11.XDefaultRootWindow.restype = ctypes.c_uint32
        # fetch current settings
        self.display = lib_x11.XOpenDisplay(None)
        if self.display is None:
            raise AttributeError()
        self.root_window = lib_x11.XDefaultRootWindow(self.display)

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

    def get_dbus_idle(self) -> float:
        self.lib_xss.XScreenSaverQueryInfo(self.display, self.root_window, self.xss_info)
        return self.xss_info.contents.idle

    def _load_lib(self, name: str) -> Any:
        path = ctypes.util.find_library(name)
        if path is None:
            raise OSError(f"Could not find library `{name}`")
        return ctypes.cdll.LoadLibrary(path)


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
        return current_tick - last_tick
