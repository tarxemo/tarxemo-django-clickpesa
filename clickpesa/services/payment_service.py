"""
Payment service for ClickPesa mobile money payments.
Handles USSD-PUSH payment operations.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from ..config import config
from ..constants import APIEndpoints, Currency
from ..exceptions import PaymentError, ValidationError
from ..utils.http_client import HTTPClient
from ..utils.validators import (
    validate_phone_number, validate_amount, 
    validate_currency, validate_order_reference
)
from ..utils.checksum import generate_checksum
from .auth_service import AuthService

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for mobile money payment operations.
    Handles preview, initiation, and status queries.
    """
    
    def __init__(self):
        self.http_client = HTTPClient(config.api_base_url)
        self.auth_service = AuthService()
    
    def preview_ussd_push(
        self,
        amount: float,
        currency: str,
        order_reference: str,
        phone_number: str,
        fetch_sender_details: bool = False
    ) -> Dict[str, Any]:
        """
        Preview USSD-PUSH payment request.
        Validates payment details and returns available payment methods.
        
        Args:
            amount: Payment amount
            currency: Currency code (TZS or USD)
            order_reference: Unique order reference
            phone_number: Customer phone number
            fetch_sender_details: Whether to fetch sender details
            
        Returns:
            Dictionary containing:
                - activeMethods: List of available payment methods with fees
                - sender: Sender details (if fetch_sender_details=True)
                
        Raises:
            ValidationError: If input validation fails
            PaymentError: If preview request fails
        """
        logger.info(f"Previewing payment for order: {order_reference}")
        
        # Validate inputs
        try:
            validated_amount = validate_amount(amount)
            validated_currency = validate_currency(currency)
            validated_phone = validate_phone_number(phone_number)
            validated_reference = validate_order_reference(order_reference)
        except (ValidationError, Exception) as e:
            logger.error(f"Validation failed: {str(e)}")
            raise
        
        # Prepare payload
        payload = {
            'amount': str(validated_amount),
            'currency': validated_currency,
            'orderReference': validated_reference,
            'phoneNumber': validated_phone,
            'fetchSenderDetails': fetch_sender_details
        }
        
        # Add checksum if enabled
        if config.enable_checksum:
            payload['checksum'] = generate_checksum(payload, config.checksum_secret)
        
        try:
            # Get auth headers
            headers = self.auth_service.get_auth_header()
            
            # Make API request
            response = self.http_client.post(
                endpoint=APIEndpoints.PREVIEW_USSD_PUSH,
                data=payload,
                headers=headers
            )
            
            logger.info(f"Payment preview successful for order: {order_reference}")
            return response
        
        except Exception as e:
            logger.error(f"Payment preview failed: {str(e)}")
            raise PaymentError(f"Failed to preview payment: {str(e)}")
    
    def initiate_ussd_push(
        self,
        amount: float,
        currency: str,
        order_reference: str,
        phone_number: str
    ) -> Dict[str, Any]:
        """
        Initiate USSD-PUSH payment request.
        Sends payment request to customer's mobile device.
        
        Args:
            amount: Payment amount
            currency: Currency code (TZS or USD)
            order_reference: Unique order reference
            phone_number: Customer phone number
            
        Returns:
            Dictionary containing:
                - id: Transaction ID
                - status: Transaction status
                - channel: Payment channel
                - orderReference: Order reference
                - collectedAmount: Amount to be collected
                - collectedCurrency: Currency
                - createdAt: Creation timestamp
                - clientId: Client ID
                
        Raises:
            ValidationError: If input validation fails
            PaymentError: If initiation fails
        """
        logger.info(f"Initiating payment for order: {order_reference}")
        
        # Validate inputs
        try:
            validated_amount = validate_amount(amount)
            validated_currency = validate_currency(currency)
            validated_phone = validate_phone_number(phone_number)
            validated_reference = validate_order_reference(order_reference)
        except (ValidationError, Exception) as e:
            logger.error(f"Validation failed: {str(e)}")
            raise
        
        # Prepare payload
        payload = {
            'amount': str(validated_amount),
            'currency': validated_currency,
            'orderReference': validated_reference,
            'phoneNumber': validated_phone
        }
        
        # Add checksum if enabled
        if config.enable_checksum:
            payload['checksum'] = generate_checksum(payload, config.checksum_secret)
        
        try:
            # Get auth headers
            headers = self.auth_service.get_auth_header()
            
            # Make API request
            response = self.http_client.post(
                endpoint=APIEndpoints.INITIATE_USSD_PUSH,
                data=payload,
                headers=headers
            )
            
            logger.info(
                f"Payment initiated successfully. "
                f"Order: {order_reference}, Transaction ID: {response.get('id')}"
            )
            return response
        
        except Exception as e:
            logger.error(f"Payment initiation failed: {str(e)}")
            raise PaymentError(f"Failed to initiate payment: {str(e)}")
    
    def query_payment_status(self, order_reference: str) -> Dict[str, Any]:
        """
        Query payment status by order reference.
        
        Args:
            order_reference: Order reference to query
            
        Returns:
            Dictionary containing:
                - id: Transaction ID
                - status: Payment status
                - paymentReference: Payment reference
                - orderReference: Order reference
                - collectedAmount: Amount collected
                - collectedCurrency: Currency
                - message: Status message
                - customer: Customer details
                - createdAt: Creation timestamp
                - updatedAt: Last update timestamp
                
        Raises:
            ValidationError: If order reference is invalid
            PaymentError: If query fails
        """
        logger.info(f"Querying payment status for order: {order_reference}")
        
        # Validate order reference
        try:
            validated_reference = validate_order_reference(order_reference)
        except ValidationError as e:
            logger.error(f"Validation failed: {str(e)}")
            raise
        
        try:
            # Get auth headers
            headers = self.auth_service.get_auth_header()
            
            # Make API request
            endpoint = APIEndpoints.QUERY_PAYMENT.format(orderReference=validated_reference)
            response = self.http_client.get(
                endpoint=endpoint,
                headers=headers
            )
            
            # Check if response is a list (API docs hint it might be list of transactions)
            if isinstance(response, list) and len(response) > 0:
                response = response[0]
            elif isinstance(response, list) and len(response) == 0:
                 raise PaymentError("No payment records found for this reference")

            logger.info(
                f"Payment status retrieved. "
                f"Order: {order_reference}, Status: {response.get('status')}"
            )
            return response
        
        except Exception as e:
            logger.error(f"Payment status query failed: {str(e)}")
            raise PaymentError(f"Failed to query payment status: {str(e)}")
    
    def get_available_methods(
        self,
        amount: float,
        currency: str,
        order_reference: str,
        phone_number: str
    ) -> List[Dict[str, Any]]:
        """
        Get list of available payment methods for a transaction.
        
        Args:
            amount: Payment amount
            currency: Currency code
            order_reference: Order reference
            phone_number: Customer phone number
            
        Returns:
            List of available payment methods with fees
        """
        preview = self.preview_ussd_push(
            amount=amount,
            currency=currency,
            order_reference=order_reference,
            phone_number=phone_number,
            fetch_sender_details=False
        )
        
        return preview.get('activeMethods', [])
