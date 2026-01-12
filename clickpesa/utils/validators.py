"""
Validation utilities for ClickPesa payment operations.
"""

import re
from decimal import Decimal
from typing import Optional
from ..constants import Currency, TANZANIA_COUNTRY_CODE, PHONE_NUMBER_LENGTH
from ..exceptions import InvalidPhoneNumberError, InvalidAmountError, ValidationError


def validate_phone_number(phone: str, country_code: str = TANZANIA_COUNTRY_CODE) -> str:
    """
    Validate and format phone number for Tanzania.
    
    Args:
        phone: Phone number to validate
        country_code: Expected country code (default: 255 for Tanzania)
        
    Returns:
        Validated phone number in format: 255XXXXXXXXX
        
    Raises:
        InvalidPhoneNumberError: If phone number is invalid
    """
    if not phone:
        raise InvalidPhoneNumberError("Phone number is required")
    
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', str(phone))
    
    # Handle different formats
    if phone.startswith('0'):
        # Convert 0712345678 to 255712345678
        phone = country_code + phone[1:]
    elif phone.startswith('+'):
        # Remove + sign
        phone = phone[1:]
    elif not phone.startswith(country_code):
        # Assume it's missing country code
        phone = country_code + phone
    
    # Validate length
    if len(phone) != PHONE_NUMBER_LENGTH:
        raise InvalidPhoneNumberError(
            f"Phone number must be {PHONE_NUMBER_LENGTH} digits including country code. "
            f"Got: {phone} ({len(phone)} digits)"
        )
    
    # Validate country code
    if not phone.startswith(country_code):
        raise InvalidPhoneNumberError(
            f"Phone number must start with {country_code}. Got: {phone}"
        )
    
    # Validate it's all digits
    if not phone.isdigit():
        raise InvalidPhoneNumberError(
            f"Phone number must contain only digits. Got: {phone}"
        )
    
    return phone


def validate_amount(amount: float, min_amount: float = 100, max_amount: Optional[float] = None) -> Decimal:
    """
    Validate payment/payout amount.
    
    Args:
        amount: Amount to validate
        min_amount: Minimum allowed amount (default: 100 TZS)
        max_amount: Maximum allowed amount (optional)
        
    Returns:
        Validated amount as Decimal
        
    Raises:
        InvalidAmountError: If amount is invalid
    """
    try:
        amount = Decimal(str(amount))
    except (ValueError, TypeError):
        raise InvalidAmountError(f"Invalid amount format: {amount}")
    
    if amount <= 0:
        raise InvalidAmountError(f"Amount must be greater than zero. Got: {amount}")
    
    if amount < Decimal(str(min_amount)):
        raise InvalidAmountError(
            f"Amount must be at least {min_amount}. Got: {amount}"
        )
    
    if max_amount and amount > Decimal(str(max_amount)):
        raise InvalidAmountError(
            f"Amount must not exceed {max_amount}. Got: {amount}"
        )
    
    # Ensure max 2 decimal places
    if amount.as_tuple().exponent < -2:
        raise InvalidAmountError(
            f"Amount can have at most 2 decimal places. Got: {amount}"
        )
    
    return amount


def validate_currency(currency: str) -> str:
    """
    Validate currency code.
    
    Args:
        currency: Currency code to validate
        
    Returns:
        Validated currency code
        
    Raises:
        ValidationError: If currency is invalid
    """
    if not currency:
        raise ValidationError("Currency is required")
    
    currency = currency.upper()
    
    valid_currencies = [c.value for c in Currency]
    if currency not in valid_currencies:
        raise ValidationError(
            f"Invalid currency: {currency}. "
            f"Supported currencies: {', '.join(valid_currencies)}"
        )
    
    return currency


def validate_order_reference(reference: str, max_length: int = 100) -> str:
    """
    Validate order reference.
    
    Args:
        reference: Order reference to validate
        max_length: Maximum allowed length
        
    Returns:
        Validated order reference
        
    Raises:
        ValidationError: If reference is invalid
    """
    if not reference:
        raise ValidationError("Order reference is required")
    
    reference = str(reference).strip()
    
    if not reference:
        raise ValidationError("Order reference cannot be empty")
    
    if len(reference) > max_length:
        raise ValidationError(
            f"Order reference too long. Maximum {max_length} characters. "
            f"Got: {len(reference)} characters"
        )
    
    # Check for valid characters (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', reference):
        raise ValidationError(
            "Order reference can only contain letters, numbers, hyphens, and underscores"
        )
    
    return reference


def validate_email(email: Optional[str]) -> Optional[str]:
    """
    Validate email address.
    
    Args:
        email: Email to validate
        
    Returns:
        Validated email or None
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        return None
    
    email = email.strip()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError(f"Invalid email format: {email}")
    
    return email
