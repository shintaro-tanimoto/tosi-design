import inspect

from nmincity.backend import NetworkBackend
from nmincity.backend.arcpy_backend import ArcpyBackend


def test_arcpy_backend_imports_without_arcpy():
    assert issubclass(ArcpyBackend, NetworkBackend)


def test_arcpy_backend_implements_network_backend():
    assert ArcpyBackend.__abstractmethods__ == frozenset()


def test_fallback_speed_comes_from_config():
    """Shape_Length フォールバックの速度は config（徒歩 4.8 km/h）に従う（要件 §6.4）."""

    source = inspect.getsource(ArcpyBackend.service_area)
    assert "MODE_SPEED_KMH" in source
    assert "5_000" not in source
