from fastapi import FastAPI

from app.api.jobs import router as jobs_router

app = FastAPI(title="AI Content Factory")


app.include_router(jobs_router)


@app.get("/")
def root():
    return {"status": "running"}