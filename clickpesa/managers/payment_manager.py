"""
Payment manager for high-level payment workflow orchestration.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from ..constants import Currency, PaymentStatus
from ..exceptions import PaymentError, DuplicateOrderReferenceError
from ..models import PaymentTransaction
from ..services.payment_service import PaymentService
from ..utils.formatters import parse_clickpesa_amount
from ..signals import payment_status_changed

logger = logging.getLogger(__name__)


class PaymentManager:
    """
    High-level manager for payment operations.
    Orchestrates payment workflow and manages database records.
    """
    
    def __init__(self):
        self.payment_service = PaymentService()
    
    def create_payment(
        self,
        amount: float,
        phone_number: str,
        order_reference: str,
        currency: str = Currency.TZS.value,
        preview_first: bool = True,
        user=None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentTransaction:
        """
        Create a new payment transaction.
        Optionally previews before initiating.
        
        Args:
            amount: Payment amount
            phone_number: Customer phone number
            order_reference: Unique order reference
            currency: Currency code (default: TZS)
            preview_first: Whether to preview before initiating
            user: User instance (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            PaymentTransaction instance
            
        Raises:
            DuplicateOrderReferenceError: If order reference already exists
            PaymentError: If payment creation fails
        """
        logger.info(f"Creating payment for order: {order_reference}")
        
        # Check for duplicate order reference
        if PaymentTransaction.objects.filter(order_reference=order_reference).exists():
            raise DuplicateOrderReferenceError(
                f"Payment with order reference '{order_reference}' already exists"
            )
        
        # Preview payment if requested
        if preview_first:
            try:
                preview = self.payment_service.preview_ussd_push(
                    amount=amount,
                    currency=currency,
                    order_reference=order_reference,
                    phone_number=phone_number,
                    fetch_sender_details=True
                )
                logger.info(f"Payment preview completed for order: {order_reference}")
                
                # Check if any payment methods are available
                active_methods = preview.get('activeMethods', [])
                available = any(m.get('status') == 'AVAILABLE' for m in active_methods)
                
                if not available:
                    raise PaymentError(
                        "No payment methods available for this transaction. "
                        "Please check phone number and try again."
                    )
            
            except Exception as e:
                logger.error(f"Payment preview failed: {str(e)}")
                raise
        
        # Initiate payment
        try:
            response = self.payment_service.initiate_ussd_push(
                amount=amount,
                currency=currency,
                order_reference=order_reference,
                phone_number=phone_number
            )
        except Exception as e:
            logger.error(f"Payment initiation failed: {str(e)}")
            raise
        
        # Create database record
        try:
            with transaction.atomic():
                payment = PaymentTransaction.objects.create(
                    id=response.get('id'),
                    order_reference=order_reference,
                    status=response.get('status', PaymentStatus.PROCESSING.value),
                    channel=response.get('channel', ''),
                    channel_provider=response.get('channelProvider'),
                    collected_amount=parse_clickpesa_amount(response.get('collectedAmount', 0)),
                    collected_currency=response.get('collectedCurrency', currency),
                    customer_phone=phone_number,
                    raw_response=response,
                    user=user,
                    metadata=metadata or {}
                )
                
                logger.info(
                    f"Payment transaction created. "
                    f"Order: {order_reference}, ID: {payment.id}"
                )
                
                # Emit signal
                payment_status_changed.send(
                    sender=PaymentTransaction,
                    instance=payment,
                    created=True,
                    new_status=payment.status,
                    old_status=None
                )
                
                return payment
        
        except Exception as e:
            logger.error(f"Failed to create payment record: {str(e)}")
            raise PaymentError(f"Payment initiated but failed to save record: {str(e)}")
    
    def check_payment_status(self, order_reference: str) -> PaymentTransaction:
        """
        Check and update payment status.
        
        Args:
            order_reference: Order reference to check
            
        Returns:
            Updated PaymentTransaction instance
            
        Raises:
            PaymentError: If payment not found or status check fails
        """
        logger.info(f"Checking payment status for order: {order_reference}")
        
        # Get payment from database
        try:
            payment = PaymentTransaction.objects.get(order_reference=order_reference)
        except PaymentTransaction.DoesNotExist:
            raise PaymentError(f"Payment with order reference '{order_reference}' not found")
        
        # If payment is already completed, return it
        if payment.is_successful() or payment.is_failed():
            logger.info(f"Payment already in final state: {payment.status}")
            return payment
        
        # Query status from API
        try:
            response = self.payment_service.query_payment_status(order_reference)
        except Exception as e:
            logger.error(f"Failed to query payment status: {str(e)}")
            raise
        
        # Update payment record
        try:
            old_status = payment.status
            with transaction.atomic():
                payment.status = response.get('status', payment.status)
                payment.payment_reference = response.get('paymentReference')
                payment.collected_amount = parse_clickpesa_amount(
                    response.get('collectedAmount', payment.collected_amount)
                )
                payment.message = response.get('message')
                payment.raw_response = response
                
                # Update customer details if available
                customer = response.get('customer', {})
                if customer:
                    payment.customer_name = customer.get('customerName')
                    payment.customer_email = customer.get('customerEmail')
                
                # Set completed timestamp if successful
                if payment.is_successful() and not payment.completed_at:
                    payment.completed_at = timezone.now()
                
                payment.save()
                
                logger.info(
                    f"Payment status updated. "
                    f"Order: {order_reference}, Status: {payment.status}"
                )
                
                # Emit signal if status changed
                if old_status != payment.status:
                    payment_status_changed.send(
                        sender=PaymentTransaction,
                        instance=payment,
                        created=False,
                        new_status=payment.status,
                        old_status=old_status
                    )
                
                return payment
        
        except Exception as e:
            logger.error(f"Failed to update payment record: {str(e)}")
            raise PaymentError(f"Failed to update payment status: {str(e)}")
    
    def get_payment_by_reference(self, order_reference: str) -> Optional[PaymentTransaction]:
        """
        Get payment transaction by order reference.
        
        Args:
            order_reference: Order reference
            
        Returns:
            PaymentTransaction instance or None
        """
        try:
            return PaymentTransaction.objects.get(order_reference=order_reference)
        except PaymentTransaction.DoesNotExist:
            return None
    
    def get_payment_by_id(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """
        Get payment transaction by ID.
        
        Args:
            transaction_id: ClickPesa transaction ID
            
        Returns:
            PaymentTransaction instance or None
        """
        try:
            return PaymentTransaction.objects.get(id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            return None
