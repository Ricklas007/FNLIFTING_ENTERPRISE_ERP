import pytest

from app.storage.provider import LocalStorageProvider, StorageError


def test_local_storage_provider_put_get_delete_and_health(tmp_path):
    provider = LocalStorageProvider(tmp_path / "objects")
    health = provider.health()
    assert health.status == "CONNECTED"

    stored = provider.put_bytes("documents/qa.txt", b"fnlifting", "text/plain")
    assert stored.provider == "LOCAL"
    assert stored.size_bytes == 9
    assert provider.get_bytes("documents/qa.txt") == b"fnlifting"

    provider.delete("documents/qa.txt")
    with pytest.raises(StorageError):
        provider.get_bytes("documents/qa.txt")


def test_local_storage_provider_rejects_path_traversal(tmp_path):
    provider = LocalStorageProvider(tmp_path / "objects")
    with pytest.raises(StorageError):
        provider.put_bytes("../outside.txt", b"blocked")
    with pytest.raises(StorageError):
        provider.get_bytes("documents/../../outside.txt")
