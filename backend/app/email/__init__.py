"""Transactional account-lifecycle email delivery."""

from app.email.service import EmailService, EmailSendResult, FakeEmailTransport, get_email_service

__all__ = ["EmailService", "EmailSendResult", "FakeEmailTransport", "get_email_service"]
