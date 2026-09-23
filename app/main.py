from fastapi import FastAPI

from app.api.routes import health

app = FastAPI(title="Famyard Bot")

app.include_router(health.router)
