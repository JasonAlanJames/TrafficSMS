"""Local SMS consent state changes for carrier compliance commands."""

from __future__ import annotations

from app.sms.context import SMSContext


class SMSConsentService:
    """Persist local opt-out and opt-in state for a matched account."""

    @staticmethod
    def opt_out(context: SMSContext) -> None:
        """Record an opt-out without requiring an active subscription."""

        if context.user is None:
            return

        context.user.sms_opted_out_at = context.timestamp
        context.user.sms_opt_out_type = (
            context.metadata.get("twilio_opt_out_type") or "keyword"
        )
        context.db.commit()

    @staticmethod
    def opt_in(context: SMSContext) -> None:
        """Clear a local opt-out while preserving the original consent timestamp."""

        if context.user is None:
            return

        context.user.sms_opted_out_at = None
        context.user.sms_opt_out_type = None
        context.user.sms_resumed_at = context.timestamp
        context.db.commit()

    @staticmethod
    def record_help(context: SMSContext) -> None:
        """Record compliance HELP activity for a matched account."""

        if context.user is None:
            return

        context.user.sms_last_help_at = context.timestamp
        context.db.commit()
