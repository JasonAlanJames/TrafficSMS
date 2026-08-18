from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanDefinition:
    plan: str
    sms_allowance: int
    label: str


PLAN_DEFINITIONS: dict[str, PlanDefinition] = {
    "free": PlanDefinition(plan="free", sms_allowance=0, label="Free"),
    "standard": PlanDefinition(plan="standard", sms_allowance=60, label="Standard Monthly"),
    "unlimited": PlanDefinition(plan="unlimited", sms_allowance=200, label="Unlimited Monthly"),
}

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}
PAST_DUE_SUBSCRIPTION_STATUSES = {"past_due", "unpaid"}
INACTIVE_SUBSCRIPTION_STATUSES = {
    "inactive",
    "canceled",
    "cancelled",
    "incomplete",
    "incomplete_expired",
}


def get_plan_definition(plan: str | None) -> PlanDefinition:
    normalized = (plan or "free").strip().lower()
    return PLAN_DEFINITIONS.get(normalized, PLAN_DEFINITIONS["free"])
