from app.storage.provider import S3CompatibleStorageProvider, StorageHealth


def test_minio_s3_compatible_provider_reports_config_or_external_driver_state():
    provider = S3CompatibleStorageProvider()
    provider.provider = "MINIO"
    health = provider.health()
    assert isinstance(health, StorageHealth)
    assert health.provider == "MINIO"
    assert health.status in {"CONNECTED", "NOT_CONFIGURED", "DRIVER_MISSING", "DEGRADED"}
    assert health.bucket
