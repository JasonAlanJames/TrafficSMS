from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from app.core.config import get_settings
from app.core.database import get_db
from app.services.commands import process_sms

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])


@router.post("/inbound")
async def inbound_sms(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    x_twilio_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    form = dict(await request.form())
    validator = RequestValidator(settings.twilio_auth_token)
    public_url = f"{settings.public_base_url.rstrip('/')}{request.url.path}"
    if settings.app_env != "development" and (
        not x_twilio_signature or not validator.validate(public_url, form, x_twilio_signature)
    ):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    reply = await process_sms(db, From, Body)
    twiml = MessagingResponse(); twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
