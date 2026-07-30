from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import Base, engine
from app.api import twilio_webhook, stripe_webhook, billing

settings = get_settings()
app = FastAPI(title="TrafficSMS API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(twilio_webhook.router)
app.include_router(stripe_webhook.router)
app.include_router(billing.router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}
