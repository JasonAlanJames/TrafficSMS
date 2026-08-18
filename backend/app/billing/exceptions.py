class BillingError(Exception):
    default_message = "Billing operation failed."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class InvalidPlanError(BillingError):
    default_message = "Invalid subscription plan."


class BillingConfigurationError(BillingError):
    default_message = "Stripe billing is not configured."


class SubscriptionRequiredError(BillingError):
    default_message = "An active subscription is required."


class UsageLimitExceededError(BillingError):
    default_message = "Your monthly SMS allowance has been exhausted."


class BillingPermissionError(BillingError):
    default_message = "You do not have permission to access this billing resource."


class BillingNotFoundError(BillingError):
    default_message = "The requested billing resource was not found."
