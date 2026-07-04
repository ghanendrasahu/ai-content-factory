from pathlib import Path


BASE_DIR = Path.cwd()
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"


def ensure_directories() -> None:
    for directory in (DOWNLOAD_DIR, OUTPUT_DIR, TEMP_DIR):
        directory.mkdir(parents=True, exist_ok=True)


ensure_directories()
