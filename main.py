from app.main import app
@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Content Factory API",
        "docs": "/docs",
    }