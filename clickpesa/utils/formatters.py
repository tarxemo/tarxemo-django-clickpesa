"""
Data formatting utilities for ClickPesa payment operations.
"""

from decimal import Decimal
from typing import Union
from ..constants import TANZANIA_COUNTRY_CODE


def format_phone_number(phone: str, include_plus: bool = False) -> str:
    """
    Format phone number to international format.
    
    Args:
        phone: Phone number to format
        include_plus: Whether to include + prefix
        
    Returns:
        Formatted phone number (e.g., 255712345678 or +255712345678)
    """
    # Remove all non-digit characters
    import re
    phone = re.sub(r'\D', '', str(phone))
    
    # Ensure it has country code
    if not phone.startswith(TANZANIA_COUNTRY_CODE):
        if phone.startswith('0'):
            phone = TANZANIA_COUNTRY_CODE + phone[1:]
        else:
            phone = TANZANIA_COUNTRY_CODE + phone
    
    if include_plus:
        return f"+{phone}"
    return phone


def format_amount(amount: Union[int, float, Decimal, str]) -> str:
    """
    Format amount to 2 decimal places.
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted amount string (e.g., "1000.00")
    """
    try:
        amount = Decimal(str(amount))
        return f"{amount:.2f}"
    except (ValueError, TypeError):
        return "0.00"


def format_currency(amount: Union[int, float, Decimal, str], currency: str = "TZS") -> str:
    """
    Format amount with currency symbol.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted string (e.g., "TZS 1,000.00")
    """
    try:
        amount = Decimal(str(amount))
        # Format with thousand separators
        formatted = f"{amount:,.2f}"
        return f"{currency} {formatted}"
    except (ValueError, TypeError):
        return f"{currency} 0.00"


def format_order_reference(prefix: str, identifier: Union[int, str]) -> str:
    """
    Format order reference with prefix.
    
    Args:
        prefix: Prefix for reference (e.g., "BOOKING", "REFUND")
        identifier: Unique identifier
        
    Returns:
        Formatted reference (e.g., "BOOKING-12345")
    """
    return f"{prefix}-{identifier}"


def parse_clickpesa_amount(amount: Union[str, int, float]) -> Decimal:
    """
    Parse amount from ClickPesa response.
    ClickPesa returns amounts as strings.
    
    Args:
        amount: Amount from API response
        
    Returns:
        Decimal amount
    """
    try:
        return Decimal(str(amount))
    except (ValueError, TypeError):
        return Decimal('0.00')
