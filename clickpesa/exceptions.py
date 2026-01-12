"""
Custom exceptions for ClickPesa payment operations.
"""


class ClickPesaException(Exception):
    """Base exception for all ClickPesa-related errors."""
    
    def __init__(self, message, error_code=None, response_data=None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data
        super().__init__(self.message)


class AuthenticationError(ClickPesaException):
    """Raised when authentication with ClickPesa API fails."""
    pass


class PaymentError(ClickPesaException):
    """Raised when a payment operation fails."""
    pass


class PayoutError(ClickPesaException):
    """Raised when a payout operation fails."""
    pass


class ValidationError(ClickPesaException):
    """Raised when input validation fails."""
    pass


class APIError(ClickPesaException):
    """Raised when the ClickPesa API returns an error."""
    pass


class ConfigurationError(ClickPesaException):
    """Raised when there's a configuration issue."""
    pass


class InsufficientBalanceError(PayoutError):
    """Raised when account has insufficient balance for payout."""
    pass


class InvalidPhoneNumberError(ValidationError):
    """Raised when phone number format is invalid."""
    pass


class InvalidAmountError(ValidationError):
    """Raised when amount is invalid."""
    pass


class DuplicateOrderReferenceError(ValidationError):
    """Raised when order reference already exists."""
    pass
