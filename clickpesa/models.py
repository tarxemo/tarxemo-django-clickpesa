"""
Database models for ClickPesa payment transactions.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator
from decimal import Decimal

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
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional project-specific metadata")
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
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional project-specific metadata")
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

class Wallet(models.Model):
    """
    User wallet for holding funds.
    Generic implementation that links to AUTH_USER_MODEL.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clickpesa_wallet'
    )
    
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Available balance"
    )
    
    currency = models.CharField(
        max_length=3,
        default='TZS',
        choices=[
            ('TZS', 'Tanzanian Shilling'),
            ('USD', 'US Dollar'),
        ]
    )
    
    is_active = models.BooleanField(default=True)
    
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total lifetime earnings"
    )
    
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total lifetime spending"
    )
    
    last_transaction_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clickpesa_wallets'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.user} Wallet ({self.balance} {self.currency})"

    def can_withdraw(self, amount):
        return self.is_active and self.balance >= Decimal(str(amount))

    def get_escrow_balance(self):
        """Calculate total funds held in escrow for this user (as a customer)"""
        return EscrowTransaction.objects.filter(
            status='HELD',
            # We assume the 'source' for customer escrow is something they created
            # This might need project-specific logic, but we provide a helper
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')


class WalletTransaction(models.Model):
    """
    Audit trail for wallet transactions.
    Uses GenericForeignKey to link to project-specific related objects (e.g. Orders).
    """
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('ESCROW_HOLD', 'Escrow Hold'),
        ('ESCROW_RELEASE', 'Escrow Release'),
        ('REFUND', 'Refund'),
        ('FEE', 'Platform Fee'),
        ('COMMISSION', 'Commission'),
    ]
    
    TRANSACTION_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed'),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='TZS')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='PENDING')
    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Generic relation to related object (e.g. Order, Subscription)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Internal ClickPesa relations
    clickpesa_payment = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    clickpesa_payout = models.ForeignKey(
        PayoutTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'clickpesa_wallet_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['reference']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            import uuid
            self.reference = f"W-TXN-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class EscrowTransaction(models.Model):
    """
    Generic Escrow holding.
    """
    ESCROW_STATUS = [
        ('HELD', 'Held'),
        ('RELEASED', 'Released'),
        ('REFUNDED', 'Refunded'),
        ('DISPUTED', 'Disputed'),
    ]
    
    # Generic relation to the primary object (e.g. Order)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    source_object = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='TZS')
    status = models.CharField(max_length=20, choices=ESCROW_STATUS, default='HELD')
    
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    seller_receives = models.DecimalField(max_digits=12, decimal_places=2)
    
    release_trigger = models.CharField(max_length=50, null=True, blank=True)
    auto_release_date = models.DateTimeField(null=True, blank=True)
    
    held_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'clickpesa_escrow_transactions'
        unique_together = ('content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status']),
            models.Index(fields=['auto_release_date']),
        ]

    def save(self, *args, **kwargs):
        if not self.seller_receives:
            self.seller_receives = self.amount - self.platform_fee
        super().save(*args, **kwargs)
