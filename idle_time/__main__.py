from . import IdleMonitor

monitor = IdleMonitor.get_monitor()
print(f"Idle time: {monitor.get_idle_time()}s")
