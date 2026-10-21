# API image: python deps in a build stage; runtime gets ffmpeg + wheels only.
FROM python:3.11-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Runtime pins minus the dev suite (black/ruff/pytest never reach the image).
COPY requirements.txt .
RUN grep -vE '^(black==|ruff==|pytest==|pytest-cov==)' requirements.txt > runtime.lock \
    && pip install --no-cache-dir -r runtime.lock

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Runtime binary dependencies + non-root user owning the mounted dirs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/downloads /app/outputs /app/temp /app/data \
    && chown -R appuser /app /home/appuser

WORKDIR /app

# Wheels from the build stage; the app never edits site-packages at runtime.
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Application code only — .env (and everything else ignorable) stays out of
# layers thanks to .dockerignore; secrets enter via env_file/secrets at run time.
COPY --chown=appuser app ./app

USER appuser

EXPOSE 8000

# Light readiness probe (no hardware/disk walks).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=4)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
