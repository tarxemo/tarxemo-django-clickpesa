"""
Constants and enums for ClickPesa payment operations.
"""

from enum import Enum


class PaymentStatus(str, Enum):
    """Payment transaction statuses."""
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SETTLED = "SETTLED"
    PENDING = "PENDING"


class PayoutStatus(str, Enum):
    """Payout transaction statuses."""
    AUTHORIZED = "AUTHORIZED"
    SUCCESS = "SUCCESS"
    REVERSED = "REVERSED"
    REFUNDED = "REFUNDED"
    PROCESSING = "PROCESSING"
    PENDING = "PENDING"
    FAILED = "FAILED"


class PaymentChannel(str, Enum):
    """Payment channels."""
    MOBILE_MONEY = "MOBILE MONEY"
    BANK_TRANSFER = "BANK TRANSFER"


class Currency(str, Enum):
    """Supported currencies."""
    TZS = "TZS"
    USD = "USD"


class MobileMoneyProvider(str, Enum):
    """Mobile money providers in Tanzania."""
    TIGO_PESA = "TIGO-PESA"
    M_PESA = "M-PESA"
    MPESA_TANZANIA = "MPESA TANZANIA"
    AIRTEL_MONEY = "AIRTEL-MONEY"
    HALOPESA = "HALOPESA"


class ProviderStatus(str, Enum):
    """Payment provider availability status."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class TransferType(str, Enum):
    """Bank transfer types."""
    ACH = "ACH"
    RTGS = "RTGS"


class PayoutFeeBearer(str, Enum):
    """Who bears the payout fee."""
    MERCHANT = "merchant"
    CUSTOMER = "customer"
    BOTH = "both"


# API Endpoints
class APIEndpoints:
    """ClickPesa API endpoints."""
    GENERATE_TOKEN = "/third-parties/generate-token"
    
    # Payment endpoints
    PREVIEW_USSD_PUSH = "/third-parties/payments/preview-ussd-push-request"
    INITIATE_USSD_PUSH = "/third-parties/payments/initiate-ussd-push-request"
    QUERY_PAYMENT = "/third-parties/payments/{orderReference}"
    
    # Payout endpoints
    PREVIEW_MOBILE_PAYOUT = "/third-parties/payouts/preview-mobile-money-payout"
    CREATE_MOBILE_PAYOUT = "/third-parties/payouts/create-mobile-money-payout"
    QUERY_PAYOUT = "/third-parties/payouts/{orderReference}"
    
    # Account endpoints
    ACCOUNT_BALANCE = "/third-parties/account/balance"


# Token settings
TOKEN_VALIDITY_HOURS = 1
TOKEN_REFRESH_BUFFER_MINUTES = 5  # Refresh token 5 minutes before expiry

# Phone number settings
TANZANIA_COUNTRY_CODE = "255"
PHONE_NUMBER_LENGTH = 12  # Including country code (255XXXXXXXXX)

# Default settings
DEFAULT_CURRENCY = Currency.TZS
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
