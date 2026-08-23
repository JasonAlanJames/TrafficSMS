from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse
from app.core.config import get_settings
from app.core.database import get_db
from app.sms import (
    SMSDispatcher,
    SMSIntentResolver,
    SMSParser,
    build_sms_context,
    format_sms_response,
)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio"])
sms_parser = SMSParser()
intent_resolver = SMSIntentResolver()
sms_dispatcher = SMSDispatcher()


@router.post("/inbound")
async def inbound_sms(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    x_twilio_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    """Validate an inbound Twilio message and serialize the SMS engine reply."""

    settings = get_settings()
    form = dict(await request.form())
    validator = RequestValidator(settings.twilio_auth_token)
    public_url = f"{settings.public_base_url.rstrip('/')}{request.url.path}"
    if settings.app_env != "development" and (
        not x_twilio_signature or not validator.validate(public_url, form, x_twilio_signature)
    ):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    parsed = sms_parser.parse(Body)
    context = build_sms_context(
        db=db,
        phone_number=From,
        parsed=parsed,
    )
    sms_response = await sms_dispatcher.dispatch(
        intent_resolver.resolve(parsed),
        context,
    )
    twiml = MessagingResponse()
    twiml.message(format_sms_response(sms_response))
    return Response(content=str(twiml), media_type="application/xml")

@router.post("/voice")
async def voice_call() -> Response:
    """
    Handle inbound voice calls to the TrafficSMS toll-free number.
    """

    response = VoiceResponse()

    response.say(
        (
            "Thank you for calling Traffic SMS. "
            "This service accepts text messages only. "
            "Please send your traffic request by SMS to this number. "
            "Goodbye."
        ),
        voice="alice",
    )

    response.hangup()

    return Response(
        content=str(response),
        media_type="application/xml",
    )
