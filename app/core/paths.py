from pathlib import Path

from app.config import settings

BASE_DIR = Path(settings.BASE_DIR).resolve()
DOWNLOAD_DIR = (BASE_DIR / settings.DOWNLOAD_DIR).resolve()
OUTPUT_DIR = (BASE_DIR / settings.OUTPUT_DIR).resolve()
TEMP_DIR = (BASE_DIR / settings.TEMP_DIR).resolve()


def ensure_directories() -> None:
    for directory in (DOWNLOAD_DIR, OUTPUT_DIR, TEMP_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def ensure_inside_directory(path: Path, directory: Path) -> Path:
    resolved_path = path.resolve()
    resolved_directory = directory.resolve()

    if (
        resolved_path != resolved_directory
        and resolved_directory not in resolved_path.parents
    ):
        raise ValueError(f"Path is outside allowed directory: {resolved_path}")

    return resolved_path


def cleanup_job_temp_files(job_id: str) -> None:
    for path in TEMP_DIR.glob(f"{job_id}*"):
        target = ensure_inside_directory(path, TEMP_DIR)
        if target.is_file():
            target.unlink(missing_ok=True)


ensure_directories()
