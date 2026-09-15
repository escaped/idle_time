"""Shared fixtures: isolate IdleMonitor.subclasses registry between tests."""
import pytest
import idle_time


@pytest.fixture(autouse=True)
def isolate_subclasses():
    saved = list(idle_time.IdleMonitor.subclasses)
    yield
    idle_time.IdleMonitor.subclasses[:] = saved
