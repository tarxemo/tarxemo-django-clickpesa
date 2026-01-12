"""
Database models for ClickPesa payment transactions.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .constants import (
    PaymentStatus, PayoutStatus, PaymentChannel, 
    Currency, TOKEN_VALIDITY_HOURS
)


class AuthToken(models.Model):
    """
    Stores ClickPesa JWT authentication tokens.
    Tokens are cached to avoid frequent API calls.
    """
    token = models.TextField(help_text="JWT token with Bearer prefix")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Token expiration time")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'clickpesa_auth_tokens'
        ordering = ['-created_at']
        verbose_name = 'Authentication Token'
        verbose_name_plural = 'Authentication Tokens'
    
    def __str__(self):
        return f"Token (expires: {self.expires_at})"
    
    def is_expired(self):
        """Check if token is expired."""
        return timezone.now() >= self.expires_at
    
    def is_valid(self):
        """Check if token is valid (active and not expired)."""
        return self.is_active and not self.is_expired()
    
    @classmethod
    def get_valid_token(cls):
        """Get a valid token from database if available."""
        return cls.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
    
    @classmethod
    def create_token(cls, token_string):
        """
        Create a new token and deactivate old ones.
        
        Args:
            token_string: JWT token string (with or without Bearer prefix)
            
        Returns:
            AuthToken instance
        """
        # Deactivate all existing tokens
        cls.objects.filter(is_active=True).update(is_active=False)
        
        # Ensure token has Bearer prefix
        if not token_string.startswith('Bearer '):
            token_string = f'Bearer {token_string}'
        
        # Create new token
        expires_at = timezone.now() + timedelta(hours=TOKEN_VALIDITY_HOURS)
        return cls.objects.create(
            token=token_string,
            expires_at=expires_at,
            is_active=True
        )


class PaymentTransaction(models.Model):
    """
    Stores mobile money payment transaction records.
    """
    # Transaction identifiers
    id = models.CharField(max_length=255, primary_key=True, help_text="ClickPesa transaction ID")
    order_reference = models.CharField(max_length=255, unique=True, db_index=True, help_text="Unique order reference")
    payment_reference = models.CharField(max_length=255, blank=True, null=True, help_text="Payment reference from provider")
    
    # Transaction details
    status = models.CharField(
        max_length=20,
        choices=[(status.value, status.value) for status in PaymentStatus],
        default=PaymentStatus.PROCESSING.value
    )
    channel = models.CharField(max_length=50, default=PaymentChannel.MOBILE_MONEY.value)
    channel_provider = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., TIGO-PESA, M-PESA")
    
    # Amount details
    collected_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount collected")
    collected_currency = models.CharField(max_length=3, default=Currency.TZS.value)
    
    # Customer details
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True, null=True)
    
    # Additional info
    message = models.TextField(blank=True, null=True, help_text="Status message")
    raw_response = models.JSONField(blank=True, null=True, help_text="Full API response")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Foreign key to user (optional)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clickpesa_payments'
    )
    
    class Meta:
        db_table = 'clickpesa_payment_transactions'
        ordering = ['-created_at']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        indexes = [
            models.Index(fields=['order_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['customer_phone']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.order_reference} - {self.status}"
    
    def is_successful(self):
        """Check if payment was successful."""
        return self.status in [PaymentStatus.SUCCESS.value, PaymentStatus.SETTLED.value]
    
    def is_pending(self):
        """Check if payment is still pending."""
        return self.status in [PaymentStatus.PROCESSING.value, PaymentStatus.PENDING.value]
    
    def is_failed(self):
        """Check if payment failed."""
        return self.status == PaymentStatus.FAILED.value


class PayoutTransaction(models.Model):
    """
    Stores mobile money payout transaction records.
    """
    # Transaction identifiers
    id = models.CharField(max_length=255, primary_key=True, help_text="ClickPesa payout ID")
    order_reference = models.CharField(max_length=255, unique=True, db_index=True, help_text="Unique order reference")
    
    # Transaction details
    status = models.CharField(
        max_length=20,
        choices=[(status.value, status.value) for status in PayoutStatus],
        default=PayoutStatus.PROCESSING.value
    )
    channel = models.CharField(max_length=50, default=PaymentChannel.MOBILE_MONEY.value)
    channel_provider = models.CharField(max_length=100, blank=True, null=True)
    transfer_type = models.CharField(max_length=20, blank=True, null=True, help_text="ACH or RTGS for bank transfers")
    
    # Amount details
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total amount deducted (includes fee)")
    currency = models.CharField(max_length=3, default=Currency.TZS.value)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Transaction fee")
    beneficiary_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount beneficiary receives")
    
    # Exchange details (for currency conversion)
    exchanged = models.BooleanField(default=False)
    source_currency = models.CharField(max_length=3, blank=True, null=True)
    target_currency = models.CharField(max_length=3, blank=True, null=True)
    source_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    
    # Beneficiary details
    beneficiary_account_number = models.CharField(max_length=100, help_text="Phone number or account number")
    beneficiary_account_name = models.CharField(max_length=255, blank=True, null=True)
    beneficiary_mobile_number = models.CharField(max_length=20, blank=True, null=True)
    beneficiary_email = models.EmailField(blank=True, null=True)
    beneficiary_swift_number = models.CharField(max_length=50, blank=True, null=True)
    beneficiary_routing_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Additional info
    notes = models.TextField(blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True, help_text="Full API response")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Foreign key to user (optional)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clickpesa_payouts'
    )
    
    class Meta:
        db_table = 'clickpesa_payout_transactions'
        ordering = ['-created_at']
        verbose_name = 'Payout Transaction'
        verbose_name_plural = 'Payout Transactions'
        indexes = [
            models.Index(fields=['order_reference']),
            models.Index(fields=['status']),
            models.Index(fields=['beneficiary_account_number']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Payout {self.order_reference} - {self.status}"
    
    def is_successful(self):
        """Check if payout was successful."""
        return self.status == PayoutStatus.SUCCESS.value
    
    def is_pending(self):
        """Check if payout is still pending."""
        return self.status in [PayoutStatus.PROCESSING.value, PayoutStatus.PENDING.value, PayoutStatus.AUTHORIZED.value]
    
    def is_failed(self):
        """Check if payout failed."""
        return self.status == PayoutStatus.FAILED.value
    
    def is_reversed(self):
        """Check if payout was reversed."""
        return self.status in [PayoutStatus.REVERSED.value, PayoutStatus.REFUNDED.value]
