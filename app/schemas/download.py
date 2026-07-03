from pydantic import BaseModel, HttpUrl


class DownloadRequest(BaseModel):
    url: HttpUrl


class DownloadResponse(BaseModel):
    status: str
    title: str
    file_path: str