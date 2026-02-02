# server/app/main.py
from fastapi import FastAPI

from src.readme.router import router as readme_router

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

# README generation API
app.include_router(readme_router)
