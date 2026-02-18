"""
Payout service for ClickPesa mobile money payouts.
Handles mobile money disbursements.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from ..config import config
from ..constants import APIEndpoints, Currency
from ..exceptions import PayoutError, ValidationError
from ..utils.http_client import HTTPClient
from ..utils.validators import (
    validate_phone_number, validate_amount,
    validate_currency, validate_order_reference
)
from ..utils.checksum import generate_checksum
from .auth_service import AuthService

logger = logging.getLogger(__name__)


class PayoutService:
    """
    Service for mobile money payout operations.
    Handles preview, creation, and status queries.
    """
    
    def __init__(self):
        self.http_client = HTTPClient(config.api_base_url)
        self.auth_service = AuthService()
    
    def preview_mobile_money_payout(
        self,
        amount: float,
        phone_number: str,
        currency: str,
        order_reference: str,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Preview mobile money payout.
        Validates payout details and returns fees, exchange rates, etc.
        
        Args:
            amount: Payout amount
            phone_number: Beneficiary phone number
            currency: Source currency (TZS or USD)
            order_reference: Unique order reference
            
        Returns:
            Dictionary containing:
                - amount: Total amount to be deducted (includes fee)
                - balance: Current account balance
                - channelProvider: Mobile money provider
                - fee: Transaction fee
                - exchanged: Whether currency conversion applies
                - exchange: Exchange rate details (if applicable)
                - order: Order details
                - payoutFeeBearer: Who bears the fee
                - receiver: Beneficiary details
                
        Raises:
            ValidationError: If input validation fails
            PayoutError: If preview request fails
        """
        logger.info(f"Previewing payout for order: {order_reference}")
        
        # Validate inputs
        try:
            validated_amount = validate_amount(amount)
            validated_phone = validate_phone_number(phone_number)
            validated_currency = validate_currency(currency)
            validated_reference = validate_order_reference(order_reference)
        except (ValidationError, Exception) as e:
            logger.error(f"Validation failed: {str(e)}")
            raise
        
        # Prepare payload
        payload = {
            'amount': float(validated_amount),
            'phoneNumber': validated_phone,
            'currency': validated_currency,
            'orderReference': validated_reference
        }
        
        if channel:
            payload['channel'] = channel
        
        # Add checksum if enabled
        if config.enable_checksum:
            payload['checksum'] = generate_checksum(payload, config.checksum_secret)
        
        try:
            # Get auth headers
            headers = self.auth_service.get_auth_header()
            
            # Make API request
            response = self.http_client.post(
                endpoint=APIEndpoints.PREVIEW_MOBILE_PAYOUT,
                data=payload,
                headers=headers
            )
            
            logger.info(f"Payout preview successful for order: {order_reference}")
            return response
        
        except Exception as e:
            logger.error(f"Payout preview failed: {str(e)}")
            raise PayoutError(f"Failed to preview payout: {str(e)}")
    
    def create_mobile_money_payout(
        self,
        amount: float,
        phone_number: str,
        currency: str,
        order_reference: str,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create mobile money payout.
        Initiates disbursement to beneficiary's mobile wallet.
        
        Args:
            amount: Payout amount
            phone_number: Beneficiary phone number
            currency: Source currency (TZS or USD)
            order_reference: Unique order reference
            
        Returns:
            Dictionary containing:
                - id: Payout transaction ID
                - orderReference: Order reference
                - amount: Total amount deducted
                - currency: Currency
                - fee: Transaction fee
                - exchanged: Whether currency conversion was applied
                - exchange: Exchange details (if applicable)
                - status: Payout status
                - channel: Payout channel
                - channelProvider: Provider name
                - order: Order details
                - beneficiary: Beneficiary details
                - createdAt: Creation timestamp
                - updatedAt: Last update timestamp
                
        Raises:
            ValidationError: If input validation fails
            PayoutError: If payout creation fails
        """
        logger.info(f"Creating payout for order: {order_reference}")
        
        # Validate inputs
        try:
            validated_amount = validate_amount(amount)
            validated_phone = validate_phone_number(phone_number)
            validated_currency = validate_currency(currency)
            validated_reference = validate_order_reference(order_reference)
        except (ValidationError, Exception) as e:
            logger.error(f"Validation failed: {str(e)}")
            raise
        
        # Prepare payload
        payload = {
            'amount': float(validated_amount),
            'phoneNumber': validated_phone,
            'currency': validated_currency,
            'orderReference': validated_reference
        }
        
        # Add checksum if enabled
        if config.enable_checksum:
            payload['checksum'] = generate_checksum(payload, config.checksum_secret)
        
        try:
            # Get auth headers
            headers = self.auth_service.get_auth_header()
            
            # Make API request
            response = self.http_client.post(
                endpoint=APIEndpoints.CREATE_MOBILE_PAYOUT,
                data=payload,
                headers=headers
            )
            
            logger.info(
                f"Payout created successfully. "
                f"Order: {order_reference}, Payout ID: {response.get('id')}"
            )
            return response
        
        except Exception as e:
            logger.error(f"Payout creation failed: {str(e)}")
            raise PayoutError(f"Failed to create payout: {str(e)}")
    
    def query_payout_status(self, order_reference: str) -> Dict[str, Any]:
        """
        Query payout status by order reference.
        
        Args:
            order_reference: Order reference to query
            
        Returns:
            Dictionary containing:
                - id: Payout ID
                - orderReference: Order reference
                - amount: Payout amount
                - currency: Currency
                - fee: Transaction fee
                - status: Payout status
                - channel: Payout channel
                - channelProvider: Provider name
                - transferType: Transfer type (if applicable)
                - notes: Additional notes
                - beneficiary: Beneficiary details
                - createdAt: Creation timestamp
                - updatedAt: Last update timestamp
                
        Raises:
            ValidationError: If order reference is invalid
            PayoutError: If query fails
        """
        logger.info(f"Querying payout status for order: {order_reference}")
        
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
            endpoint = APIEndpoints.QUERY_PAYOUT.format(orderReference=validated_reference)
            response = self.http_client.get(
                endpoint=endpoint,
                headers=headers
            )
            
            # Handle list response (API returns [{...}])
            if isinstance(response, list) and len(response) > 0:
                response = response[0]
            
            logger.info(
                f"Payout status retrieved. "
                f"Order: {order_reference}, Status: {response.get('status')}"
            )
            return response
        
        except Exception as e:
            logger.error(f"Payout status query failed: {str(e)}")
            raise PayoutError(f"Failed to query payout status: {str(e)}")
