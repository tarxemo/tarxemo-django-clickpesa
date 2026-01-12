"""
Payout manager for high-level payout workflow orchestration.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from ..constants import Currency, PayoutStatus
from ..exceptions import PayoutError, DuplicateOrderReferenceError
from ..models import PayoutTransaction
from ..services.payout_service import PayoutService
from ..utils.formatters import parse_clickpesa_amount

logger = logging.getLogger(__name__)


class PayoutManager:
    """
    High-level manager for payout operations.
    Orchestrates payout workflow and manages database records.
    """
    
    def __init__(self):
        self.payout_service = PayoutService()
    
    def create_payout(
        self,
        amount: float,
        phone_number: str,
        order_reference: str,
        currency: str = Currency.TZS.value,
        preview_first: bool = True,
        user=None
    ) -> PayoutTransaction:
        """
        Create a new payout transaction.
        Optionally previews before creating.
        
        Args:
            amount: Payout amount
            phone_number: Beneficiary phone number
            order_reference: Unique order reference
            currency: Source currency (default: TZS)
            preview_first: Whether to preview before creating
            user: User instance (optional)
            
        Returns:
            PayoutTransaction instance
            
        Raises:
            DuplicateOrderReferenceError: If order reference already exists
            PayoutError: If payout creation fails
        """
        logger.info(f"Creating payout for order: {order_reference}")
        
        # Check for duplicate order reference
        if PayoutTransaction.objects.filter(order_reference=order_reference).exists():
            raise DuplicateOrderReferenceError(
                f"Payout with order reference '{order_reference}' already exists"
            )
        
        # Preview payout if requested
        preview_data = None
        if preview_first:
            try:
                preview_data = self.payout_service.preview_mobile_money_payout(
                    amount=amount,
                    phone_number=phone_number,
                    currency=currency,
                    order_reference=order_reference
                )
                logger.info(f"Payout preview completed for order: {order_reference}")
                
                # Log fee information
                fee = preview_data.get('fee', 0)
                total = preview_data.get('amount', 0)
                logger.info(f"Payout preview: Amount={amount}, Fee={fee}, Total={total}")
            
            except Exception as e:
                logger.error(f"Payout preview failed: {str(e)}")
                raise
        
        # Create payout
        try:
            response = self.payout_service.create_mobile_money_payout(
                amount=amount,
                phone_number=phone_number,
                currency=currency,
                order_reference=order_reference
            )
        except Exception as e:
            logger.error(f"Payout creation failed: {str(e)}")
            raise
        
        # Create database record
        try:
            with transaction.atomic():
                # Parse exchange details
                exchange_data = response.get('exchange', {})
                exchanged = response.get('exchanged', False)
                
                # Parse beneficiary details
                beneficiary = response.get('beneficiary', {})
                
                # Parse order details
                order = response.get('order', {})
                
                payout = PayoutTransaction.objects.create(
                    id=response.get('id'),
                    order_reference=order_reference,
                    status=response.get('status', PayoutStatus.PROCESSING.value),
                    channel=response.get('channel', ''),
                    channel_provider=response.get('channelProvider'),
                    amount=parse_clickpesa_amount(response.get('amount', 0)),
                    currency=response.get('currency', currency),
                    fee=parse_clickpesa_amount(response.get('fee', 0)),
                    beneficiary_amount=parse_clickpesa_amount(beneficiary.get('amount', 0)),
                    exchanged=exchanged,
                    source_currency=exchange_data.get('sourceCurrency') if exchanged else None,
                    target_currency=exchange_data.get('targetCurrency') if exchanged else None,
                    source_amount=parse_clickpesa_amount(exchange_data.get('sourceAmount', 0)) if exchanged else None,
                    exchange_rate=parse_clickpesa_amount(exchange_data.get('rate', 0)) if exchanged else None,
                    beneficiary_account_number=beneficiary.get('accountNumber', phone_number),
                    beneficiary_account_name=beneficiary.get('accountName'),
                    raw_response=response,
                    user=user
                )
                
                logger.info(
                    f"Payout transaction created. "
                    f"Order: {order_reference}, ID: {payout.id}"
                )
                return payout
        
        except Exception as e:
            logger.error(f"Failed to create payout record: {str(e)}")
            raise PayoutError(f"Payout initiated but failed to save record: {str(e)}")
    
    def check_payout_status(self, order_reference: str) -> PayoutTransaction:
        """
        Check and update payout status.
        
        Args:
            order_reference: Order reference to check
            
        Returns:
            Updated PayoutTransaction instance
            
        Raises:
            PayoutError: If payout not found or status check fails
        """
        logger.info(f"Checking payout status for order: {order_reference}")
        
        # Get payout from database
        try:
            payout = PayoutTransaction.objects.get(order_reference=order_reference)
        except PayoutTransaction.DoesNotExist:
            raise PayoutError(f"Payout with order reference '{order_reference}' not found")
        
        # If payout is already in final state, return it
        if payout.is_successful() or payout.is_failed() or payout.is_reversed():
            logger.info(f"Payout already in final state: {payout.status}")
            return payout
        
        # Query status from API
        try:
            response = self.payout_service.query_payout_status(order_reference)
        except Exception as e:
            logger.error(f"Failed to query payout status: {str(e)}")
            raise
        
        # Update payout record
        try:
            with transaction.atomic():
                payout.status = response.get('status', payout.status)
                payout.transfer_type = response.get('transferType')
                payout.notes = response.get('notes')
                payout.raw_response = response
                
                # Update beneficiary details if available
                beneficiary = response.get('beneficiary', {})
                if beneficiary:
                    payout.beneficiary_account_name = beneficiary.get('accountName') or payout.beneficiary_account_name
                    payout.beneficiary_mobile_number = beneficiary.get('beneficiaryMobileNumber')
                    payout.beneficiary_email = beneficiary.get('beneficiaryEmail')
                    payout.beneficiary_swift_number = beneficiary.get('swiftNumber')
                    payout.beneficiary_routing_number = beneficiary.get('routingNumber')
                
                # Set completed timestamp if successful
                if payout.is_successful() and not payout.completed_at:
                    payout.completed_at = timezone.now()
                
                payout.save()
                
                logger.info(
                    f"Payout status updated. "
                    f"Order: {order_reference}, Status: {payout.status}"
                )
                return payout
        
        except Exception as e:
            logger.error(f"Failed to update payout record: {str(e)}")
            raise PayoutError(f"Failed to update payout status: {str(e)}")
    
    def get_payout_by_reference(self, order_reference: str) -> Optional[PayoutTransaction]:
        """
        Get payout transaction by order reference.
        
        Args:
            order_reference: Order reference
            
        Returns:
            PayoutTransaction instance or None
        """
        try:
            return PayoutTransaction.objects.get(order_reference=order_reference)
        except PayoutTransaction.DoesNotExist:
            return None
    
    def get_payout_by_id(self, transaction_id: str) -> Optional[PayoutTransaction]:
        """
        Get payout transaction by ID.
        
        Args:
            transaction_id: ClickPesa payout ID
            
        Returns:
            PayoutTransaction instance or None
        """
        try:
            return PayoutTransaction.objects.get(id=transaction_id)
        except PayoutTransaction.DoesNotExist:
            return None
