import ctypes
import ctypes.util
import logging
from typing import Any, List, Type

from jeepney import DBusAddress, new_method_call
from jeepney.integrate.blocking import connect_and_authenticate

logger = logging.getLogger(name="idle_time")


class IdleMonitor:
    subclasses: List[Type["IdleMonitor"]] = []

    def __init__(self, *, idle_threshold: int = 120) -> None:
        self.idle_threshold = idle_threshold

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.subclasses.append(cls)

    @classmethod
    def get_monitor(cls, **kwargs) -> "IdleMonitor":
        """
        Return the first available idle monitor.

        Raises `RuntimeError` if no usable monitor could be found.
        """
        for monitor_class in cls.subclasses:
            try:
                return monitor_class(**kwargs)
            except Exception:
                logger.warning("Could not load %s", monitor_class, exc_info=True)
        raise RuntimeError("Could not find a working monitor.")

    def get_idle_time(self) -> float:
        """
        Return idle time in seconds.
        """
        raise NotImplementedError()

    def is_idle(self) -> bool:
        """
        Return whether the user is idling.
        """
        return self.get_idle_time() > self.idle_threshold


try:
    import win32api
except ImportError:
    pass
else:

    class WindowsIdleMonitor(IdleMonitor):
        """
        Idle monitor for Windows.

        Based on
          * https://stackoverflow.com/q/911856
        """

        def get_idle_time(self) -> float:
            return (win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000


class GnomeWaylandIdleMonitor(IdleMonitor):
    """
    Idle monitor for gnome running on wayland.

    Based on
      * https://unix.stackexchange.com/a/492328
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        address = DBusAddress(
            "/org/gnome/Mutter/IdleMonitor/Core",
            bus_name="org.gnome.Mutter.IdleMonitor",
            interface="org.gnome.Mutter.IdleMonitor",
        )
        self.connection = connect_and_authenticate(bus="SESSION")
        self.message = new_method_call(address, "GetIdletime")

    def get_idle_time(self) -> float:
        reply = self.connection.send_and_get_reply(self.message)
        idle_time = reply[0]
        return idle_time / 1000


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

    def get_idle_time(self) -> float:
        self.lib_xss.XScreenSaverQueryInfo(self.display, self.root_window, self.xss_info)
        return self.xss_info.contents.idle / 1000

    def _load_lib(self, name: str) -> Any:
        path = ctypes.util.find_library(name)
        if path is None:
            raise OSError(f"Could not find library `{name}`")
        return ctypes.cdll.LoadLibrary(path)
