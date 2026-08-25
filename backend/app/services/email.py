from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from functools import lru_cache
from html import escape
from urllib.parse import quote

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailContent:
    recipient: str
    subject: str
    text_body: str
    html_body: str


class EmailService:
    def send_verification_email(self, *, recipient: str, token: str) -> bool:
        raise NotImplementedError

    def send_resend_verification_email(self, *, recipient: str, token: str) -> bool:
        raise NotImplementedError

    def send_password_reset_email(self, *, recipient: str, token: str) -> bool:
        raise NotImplementedError

    def send_email_change_verification_email(
        self,
        *,
        recipient: str,
        token: str,
    ) -> bool:
        raise NotImplementedError


class SmtpEmailService(EmailService):
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_verification_email(self, *, recipient: str, token: str) -> bool:
        return self._deliver(
            self._build_verification_email(
                recipient=recipient,
                token=token,
                requested_again=False,
            )
        )

    def send_resend_verification_email(self, *, recipient: str, token: str) -> bool:
        return self._deliver(
            self._build_verification_email(
                recipient=recipient,
                token=token,
                requested_again=True,
            )
        )

    def send_password_reset_email(self, *, recipient: str, token: str) -> bool:
        return self._deliver(
            self._build_password_reset_email(
                recipient=recipient,
                token=token,
            )
        )

    def send_email_change_verification_email(
        self,
        *,
        recipient: str,
        token: str,
    ) -> bool:
        return self._deliver(
            self._build_email_change_verification_email(
                recipient=recipient,
                token=token,
            )
        )

    def _deliver(self, content: EmailContent) -> bool:
        logger.info(
            "Email queued recipient=%s subject=%s",
            content.recipient,
            content.subject,
        )

        if not self.settings.email_enabled:
            logger.info(
                "Email skipped recipient=%s subject=%s reason=disabled",
                content.recipient,
                content.subject,
            )
            return False

        if not self._is_configured:
            logger.error(
                "SMTP error recipient=%s subject=%s detail=SMTP is not configured",
                content.recipient,
                content.subject,
            )
            return False

        message = self._build_message(content)

        try:
            with self._connect() as smtp:
                logger.info(
                    "SMTP connected recipient=%s subject=%s host=%s port=%s",
                    content.recipient,
                    content.subject,
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                )
                smtp.send_message(message)
                logger.info(
                    "Email delivered recipient=%s subject=%s",
                    content.recipient,
                    content.subject,
                )
                return True
        except Exception:
            logger.exception(
                "SMTP error recipient=%s subject=%s",
                content.recipient,
                content.subject,
            )
            return False

    @property
    def _is_configured(self) -> bool:
        return bool(
            self.settings.smtp_host.strip()
            and self.settings.smtp_port > 0
            and self.settings.mail_from.strip()
        )

    def _build_message(self, content: EmailContent) -> EmailMessage:
        message = EmailMessage()
        message["From"] = formataddr(
            (
                self.settings.mail_from_name.strip(),
                self.settings.mail_from.strip(),
            )
        )
        message["To"] = content.recipient
        message["Subject"] = content.subject
        if self.settings.email_reply_to.strip():
            message["Reply-To"] = self.settings.email_reply_to.strip()
        message.set_content(content.text_body)
        message.add_alternative(content.html_body, subtype="html")
        return message

    def _connect(self) -> smtplib.SMTP:
        timeout_seconds = self.settings.smtp_timeout_seconds

        if self.settings.smtp_ssl:
            smtp = smtplib.SMTP_SSL(
                host=self.settings.smtp_host,
                port=self.settings.smtp_port,
                timeout=timeout_seconds,
            )
        else:
            smtp = smtplib.SMTP(
                host=self.settings.smtp_host,
                port=self.settings.smtp_port,
                timeout=timeout_seconds,
            )
            smtp.ehlo()
            if self.settings.smtp_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()

        if self.settings.smtp_username:
            smtp.login(
                self.settings.smtp_username,
                self.settings.smtp_password,
            )

        return smtp

    def _build_verification_email(
        self,
        *,
        recipient: str,
        token: str,
        requested_again: bool,
    ) -> EmailContent:
        subject = "Verify your TrafficSMS account"
        verification_url = self._verification_url(token)
        requested_copy = (
            "A new verification link was requested for your account."
            if requested_again
            else "Thanks for registering with TrafficSMS."
        )
        expires_in_hours = self.settings.email_verification_token_expire_hours

        text_body = (
            "Verify your TrafficSMS account\n\n"
            f"{requested_copy}\n\n"
            "Verify your account:\n"
            f"{verification_url}\n\n"
            f"This link expires in {expires_in_hours} hours.\n"
            "If you did not request this, you can ignore this email.\n\n"
            f"Support: {self.settings.support_url}"
        )
        html_body = (
            "<html><body style=\"margin:0;padding:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#14213d;\">"
            "<div style=\"max-width:640px;margin:0 auto;padding:32px 20px;\">"
            "<div style=\"background:#ffffff;border-radius:20px;padding:32px;box-shadow:0 18px 48px rgba(20,33,61,0.08);\">"
            "<p style=\"margin:0 0 12px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#64748b;\">TrafficSMS</p>"
            "<h1 style=\"margin:0 0 16px;font-size:28px;line-height:1.2;\">Verify your TrafficSMS account</h1>"
            f"<p style=\"margin:0 0 16px;font-size:16px;line-height:1.6;\">{requested_copy}</p>"
            "<p style=\"margin:0 0 24px;font-size:16px;line-height:1.6;\">"
            "Use the button below to verify your email address and activate your TrafficSMS sign-in."
            "</p>"
            f"<p style=\"margin:0 0 24px;\"><a href=\"{verification_url}\" "
            "style=\"display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;padding:14px 22px;border-radius:999px;font-weight:700;\">"
            "Verify account</a></p>"
            f"<p style=\"margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;\">This link expires in {expires_in_hours} hours.</p>"
            f"<p style=\"margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;\">If the button does not work, copy and paste this URL into your browser:</p>"
            f"<p style=\"margin:0 0 24px;font-size:14px;line-height:1.6;word-break:break-word;\"><a href=\"{verification_url}\" style=\"color:#0f766e;\">{verification_url}</a></p>"
            "<p style=\"margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;\">If you did not request this, you can ignore this email.</p>"
            f"<p style=\"margin:0;font-size:14px;line-height:1.6;color:#475569;\">Need help? <a href=\"{escape(self.settings.support_url, quote=True)}\" style=\"color:#0f766e;\">TrafficSMS Support</a></p>"
            "</div></div></body></html>"
        )

        return EmailContent(
            recipient=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    def _build_password_reset_email(
        self,
        *,
        recipient: str,
        token: str,
    ) -> EmailContent:
        subject = "Reset your TrafficSMS password"
        reset_url = self._password_reset_url(token)
        expires_in_hours = self.settings.password_reset_token_expire_hours

        text_body = (
            "Reset your TrafficSMS password\n\n"
            "A password reset was requested for your TrafficSMS account.\n\n"
            "Reset your password:\n"
            f"{reset_url}\n\n"
            f"This link expires in {expires_in_hours} hour(s).\n"
            "If you did not request this, you can ignore this email.\n\n"
            f"Support: {self.settings.support_url}"
        )
        html_body = (
            "<html><body style=\"margin:0;padding:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#14213d;\">"
            "<div style=\"max-width:640px;margin:0 auto;padding:32px 20px;\">"
            "<div style=\"background:#ffffff;border-radius:20px;padding:32px;box-shadow:0 18px 48px rgba(20,33,61,0.08);\">"
            "<p style=\"margin:0 0 12px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#64748b;\">TrafficSMS</p>"
            "<h1 style=\"margin:0 0 16px;font-size:28px;line-height:1.2;\">Reset your TrafficSMS password</h1>"
            "<p style=\"margin:0 0 16px;font-size:16px;line-height:1.6;\">A password reset was requested for your TrafficSMS account.</p>"
            "<p style=\"margin:0 0 24px;font-size:16px;line-height:1.6;\">Use the button below to choose a new password.</p>"
            f"<p style=\"margin:0 0 24px;\"><a href=\"{reset_url}\" style=\"display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;padding:14px 22px;border-radius:999px;font-weight:700;\">Reset password</a></p>"
            f"<p style=\"margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;\">This link expires in {expires_in_hours} hour(s).</p>"
            "<p style=\"margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;\">If the button does not work, copy and paste this URL into your browser:</p>"
            f"<p style=\"margin:0 0 24px;font-size:14px;line-height:1.6;word-break:break-word;\"><a href=\"{reset_url}\" style=\"color:#0f766e;\">{reset_url}</a></p>"
            "<p style=\"margin:0 0 12px;font-size:14px;line-height:1.6;color:#475569;\">If you did not request this, you can ignore this email.</p>"
            f"<p style=\"margin:0;font-size:14px;line-height:1.6;color:#475569;\">Need help? <a href=\"{escape(self.settings.support_url, quote=True)}\" style=\"color:#0f766e;\">TrafficSMS Support</a></p>"
            "</div></div></body></html>"
        )

        return EmailContent(
            recipient=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    def _build_email_change_verification_email(
        self,
        *,
        recipient: str,
        token: str,
    ) -> EmailContent:
        confirmation_url = self._frontend_url(
            self.settings.email_change_verification_path,
            token,
        )
        return EmailContent(
            recipient=recipient,
            subject="Confirm your new TrafficSMS email",
            text_body=(
                "Confirm your new TrafficSMS email\n\n"
                "Confirm this new email address for your TrafficSMS account:\n"
                f"{confirmation_url}\n\n"
                f"This link expires in {self.settings.email_verification_token_expire_hours} hours.\n"
                "If you did not request this, you can ignore this email.\n\n"
                f"Support: {self.settings.support_url}"
            ),
            html_body=(
                "<html><body><h1>TrafficSMS</h1>"
                "<h2>Confirm your new TrafficSMS email</h2>"
                "<p>Confirm this new email address for your TrafficSMS account.</p>"
                f"<p><a href=\"{escape(confirmation_url, quote=True)}\">Confirm email</a></p>"
                "<p>If you did not request this, you can ignore this email.</p>"
                f"<p><a href=\"{escape(self.settings.support_url, quote=True)}\">TrafficSMS Support</a></p>"
                "</body></html>"
            ),
        )

    def _verification_url(self, token: str) -> str:
        return self._frontend_url(self.settings.email_verification_path, token)

    def _password_reset_url(self, token: str) -> str:
        return self._frontend_url(self.settings.password_reset_path, token)

    def _frontend_url(self, path: str, token: str) -> str:
        return (
            f"{self.settings.frontend_url.rstrip('/')}/"
            f"{path.lstrip('/')}?token={quote(token, safe='')}"
        )


@lru_cache
def get_email_service() -> EmailService:
    return SmtpEmailService(get_settings())
