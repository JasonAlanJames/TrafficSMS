"""Typed, configurable transactional email delivery."""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage as MIMEEmailMessage
from email.utils import formataddr
from functools import lru_cache
from html import escape
from typing import Mapping, Protocol
from urllib.parse import quote

from pydantic import EmailStr, TypeAdapter

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)
_EMAIL = TypeAdapter(EmailStr)


@dataclass(frozen=True)
class TransactionalEmail:
    to_email: str
    subject: str
    text_body: str
    html_body: str | None
    template_name: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _EMAIL.validate_python(self.to_email)
        if not self.subject.strip() or not self.text_body.strip():
            raise ValueError("Transactional email subject and text body are required.")


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    reason: str


class EmailTransport(Protocol):
    def send(self, message: TransactionalEmail) -> None: ...


class FakeEmailTransport:
    """In-memory transport for tests; it never opens a network connection."""

    def __init__(self, *, fail: bool = False, timeout: bool = False) -> None:
        self.messages: list[TransactionalEmail] = []
        self.fail = fail
        self.timeout = timeout

    def send(self, message: TransactionalEmail) -> None:
        if self.timeout:
            raise TimeoutError("Fake email transport timed out.")
        if self.fail:
            raise RuntimeError("Fake email transport failed.")
        self.messages.append(message)


class SMTPEmailTransport:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: TransactionalEmail) -> None:
        if not self.is_configured:
            raise RuntimeError("SMTP configuration is incomplete.")
        mime = MIMEEmailMessage()
        mime["From"] = formataddr((self.settings.email_from_name, self.settings.email_from_address))
        mime["To"], mime["Subject"] = message.to_email, message.subject
        if self.settings.email_reply_to:
            mime["Reply-To"] = self.settings.email_reply_to
        mime.set_content(message.text_body)
        if message.html_body:
            mime.add_alternative(message.html_body, subtype="html")
        try:
            with self._connect() as smtp:
                smtp.send_message(mime)
        except (OSError, smtplib.SMTPException) as exc:
            raise RuntimeError("SMTP delivery failed.") from exc

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.smtp_host.strip() and self.settings.smtp_port > 0 and self.settings.email_from_address.strip())

    def _connect(self) -> smtplib.SMTP:
        if self.settings.smtp_use_tls:
            smtp = smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=self.settings.smtp_timeout_seconds)
        else:
            smtp = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=self.settings.smtp_timeout_seconds)
            smtp.ehlo()
            if self.settings.smtp_use_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
        if self.settings.smtp_username:
            smtp.login(self.settings.smtp_username, self.settings.smtp_password)
        return smtp


class EmailService:
    def __init__(self, settings: Settings, transport: EmailTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport or SMTPEmailTransport(settings)

    def send_verification_email(self, *, recipient: str, token: str) -> EmailSendResult:
        return self._send(_template(recipient, "Verify your TrafficSMS account", "verification", "Thanks for creating your TrafficSMS account.", "Verify account", self.settings.email_verification_path, token, self.settings.email_verification_token_expire_hours, self.settings))

    def send_resend_verification_email(self, *, recipient: str, token: str) -> EmailSendResult:
        return self._send(_template(recipient, "Verify your TrafficSMS account", "verification_resend", "A new verification link was requested for your account.", "Verify account", self.settings.email_verification_path, token, self.settings.email_verification_token_expire_hours, self.settings))

    def send_password_reset_email(self, *, recipient: str, token: str) -> EmailSendResult:
        return self._send(_template(recipient, "Reset your TrafficSMS password", "password_reset", "A password reset was requested for your TrafficSMS account.", "Reset password", self.settings.password_reset_path, token, self.settings.password_reset_token_expire_hours, self.settings))

    def send_email_change_verification_email(self, *, recipient: str, token: str) -> EmailSendResult:
        return self._send(_template(recipient, "Confirm your new TrafficSMS email", "email_change", "Confirm this new email address for your TrafficSMS account.", "Confirm email", self.settings.email_change_verification_path, token, self.settings.email_verification_token_expire_hours, self.settings))

    def _send(self, message: TransactionalEmail) -> EmailSendResult:
        if not self.settings.email_enabled:
            logger.info("Transactional email skipped template=%s reason=disabled", message.template_name)
            return EmailSendResult(False, "disabled")
        try:
            self.transport.send(message)
        except Exception:
            logger.warning("Transactional email failed template=%s reason=delivery_failed", message.template_name)
            return EmailSendResult(False, "delivery_failed")
        logger.info("Transactional email delivered template=%s", message.template_name)
        return EmailSendResult(True, "sent")


def _template(recipient: str, subject: str, name: str, intro: str, label: str, path: str, token: str, hours: int, settings: Settings) -> TransactionalEmail:
    url = f"{settings.frontend_url.rstrip('/')}/{path.lstrip('/')}?token={quote(token, safe='')}"
    text = f"{subject}\n\n{intro}\n\n{label}:\n{url}\n\nThis link expires in {hours} hour(s). If you did not request this, you can ignore this email.\n\nSupport: {settings.support_url}"
    html = f"<html><body><h1>TrafficSMS</h1><h2>{escape(subject)}</h2><p>{escape(intro)}</p><p><a href=\"{escape(url, quote=True)}\">{escape(label)}</a></p><p>This link expires in {hours} hour(s).</p><p>If you did not request this, you can ignore this email.</p><p><a href=\"{escape(settings.support_url, quote=True)}\">TrafficSMS Support</a></p></body></html>"
    return TransactionalEmail(recipient, subject, text, html, name)


@lru_cache
def get_email_service() -> EmailService:
    return EmailService(get_settings())
