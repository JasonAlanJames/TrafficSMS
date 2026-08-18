class AuthenticationError(Exception):
    default_message = "Authentication failed."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class InvalidCredentialsError(AuthenticationError):
    default_message = "Invalid email or password."


class AccountLockedError(AuthenticationError):
    default_message = "This account has been temporarily locked."

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: int | None = None,
    ):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message or self.default_message)


class AccountDisabledError(AuthenticationError):
    default_message = "This account has been disabled."


class EmailNotVerifiedError(AuthenticationError):
    default_message = "Email address has not been verified."


class InvalidTokenError(AuthenticationError):
    default_message = "The supplied authentication token is invalid."


class TokenExpiredError(AuthenticationError):
    default_message = "Authentication token has expired."


class InvalidRefreshTokenError(AuthenticationError):
    default_message = "Refresh token is invalid or has expired."


class UserAlreadyExistsError(AuthenticationError):
    default_message = "A user with those credentials already exists."


class AuthenticationRateLimitError(AuthenticationError):
    default_message = "Too many authentication attempts. Please try again shortly."

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: int | None = None,
    ):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message or self.default_message)


class PasswordReuseError(AuthenticationError):
    default_message = "New password must be different from the current password."
