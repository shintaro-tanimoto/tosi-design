from nmincity.backend import NetworkBackend
from nmincity.backend.arcpy_backend import ArcpyBackend


def test_arcpy_backend_imports_without_arcpy():
    assert issubclass(ArcpyBackend, NetworkBackend)


def test_arcpy_backend_implements_network_backend():
    assert ArcpyBackend.__abstractmethods__ == frozenset()
