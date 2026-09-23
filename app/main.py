from fastapi import FastAPI

from app.api.routes import health, webhook

app = FastAPI(title="Famyard Bot")

app.include_router(health.router)
app.include_router(webhook.router)
