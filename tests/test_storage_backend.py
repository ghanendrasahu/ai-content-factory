from app.core.paths import OUTPUT_DIR
from app.services.storage_backend import LocalStorage


def test_local_storage_exists_and_url_for():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "test_storage_asset.mp4"
    path.write_bytes(b"data")
    storage = LocalStorage()

    assert storage.exists(path)
    assert storage.url_for(path).endswith("asset.mp4")
