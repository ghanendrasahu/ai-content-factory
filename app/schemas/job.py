from pydantic import BaseModel, HttpUrl


class DownloadJobRequest(BaseModel):
    url: HttpUrl


class PublishJobRequest(BaseModel):
    """Options for publishing a rendered job to YouTube."""

    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    privacy_status: str | None = None
    dry_run: bool = False
