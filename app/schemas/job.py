from pydantic import BaseModel, HttpUrl


class DownloadJobRequest(BaseModel):
    url: HttpUrl
