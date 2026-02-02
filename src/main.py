# server/app/main.py
from fastapi import FastAPI

from src.readme.router import router as readme_router

app = FastAPI()

@app.get("/", tags=["health"])
def root():
    return {
        "service": "subtext-backend",
        "status": "ok",
        "docs": "/docs",
        "readme_api": "/api/readme/generate",
    }

# README generation API
app.include_router(readme_router)
