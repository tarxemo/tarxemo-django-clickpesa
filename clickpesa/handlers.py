import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

from clickpesa.models import Wallet, WalletTransaction, EscrowTransaction
from clickpesa.signals import payment_status_changed, payout_status_changed
from clickpesa.managers.wallet_manager import WalletManager

logger = logging.getLogger(__name__)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created: bool, **kwargs):
    """Automatically create a wallet when a new user is created."""
    if created:
        try:
            WalletManager.get_or_create_wallet(instance)
        except Exception as e:
            logger.error(f"Failed to create wallet for user {instance}: {str(e)}")

@receiver(payment_status_changed)
def handle_clickpesa_payment_status(sender, instance, new_status, old_status=None, created=False, **kwargs):
    """
    Handle ClickPesa payment success by creating an escrow hold.
    """
    if new_status not in ['SUCCESS', 'SETTLED']:
        return
    
    # We use instance.user if available (which we added to PaymentTransaction)
    if not instance.user:
        logger.warning(f"PaymentTransaction {instance.id} has no associated user. Cannot hold escrow.")
        return

    metadata = instance.metadata or {}
    
    # Check if this is a direct wallet deposit
    if metadata.get('transaction_type') == 'WALLET_DEPOSIT':
        wm.deposit(
            wallet=WalletManager.get_or_create_wallet(instance.user),
            amount=instance.collected_amount,
            transaction_type='DEPOSIT',
            description=f"Wallet deposit via {instance.channel}",
            metadata={'clickpesa_payment_id': instance.id}
        )
        return

    wm = WalletManager()
    with transaction.atomic():
        # Calculate platform fee (can be passed via metadata or library settings)
        fee_pct = Decimal(str(getattr(settings, 'CLICKPESA_ESCROW_FEE_PCT', '2.5')))
        fee = (instance.collected_amount * fee_pct) / Decimal('100')
        
        # We need a 'source_object' (e.g. Order). 
        # In a generic library, we don't know the Order model.
        # But we can store the association in the EscrowTransaction via generic FK.
        # The project must ensure it sends the association, OR we use the PaymentTransaction as a proxy.
        
        # For now, we create the escrow linked to the PaymentTransaction itself if no other object is provided.
        # But usually, it should be linked to the Order.
        # We can look for 'source_content_type' and 'source_object_id' in instance.metadata
        
        # Optimization: We'll link the escrow to the PaymentTransaction as a fallback.
        # Try to resolve source object from metadata
        source_object = instance
        try:
            if 'source_content_type' in metadata and 'source_object_id' in metadata:
                from django.contrib.contenttypes.models import ContentType
                app_label, model = metadata['source_content_type'].split('.')
                ct = ContentType.objects.get(app_label=app_label, model=model)
                source_object = ct.get_object_for_this_type(id=metadata['source_object_id'])
        except Exception:
            pass

        wm.hold_escrow(
            source_object=source_object,
            amount=instance.collected_amount,
            platform_fee=fee,
            metadata={'clickpesa_payment_id': instance.id}
        )

@receiver(payout_status_changed)
def handle_clickpesa_payout_status(sender, instance, new_status, old_status=None, created=False, **kwargs):
    """
    Handle payout status changes for withdrawals.
    """
    wallet_txn = WalletTransaction.objects.filter(
        clickpesa_payout=instance,
        transaction_type='WITHDRAWAL'
    ).first()
    
    if not wallet_txn:
        return
    
    with transaction.atomic():
        if new_status == 'SUCCESS':
            wallet_txn.status = 'COMPLETED'
            wallet_txn.completed_at = timezone.now()
            wallet_txn.save(update_fields=['status', 'completed_at'])
            
            # Update wallet statistics
            wallet = wallet_txn.wallet
            wallet.total_spent += wallet_txn.amount
            wallet.save(update_fields=['total_spent'])
            
        elif new_status == 'FAILED':
            wallet_txn.status = 'FAILED'
            wallet_txn.save(update_fields=['status'])
            
            # Reverse deduction
            wallet = wallet_txn.wallet
            wm = WalletManager()
            wm.deposit(
                wallet=wallet,
                amount=wallet_txn.amount,
                transaction_type='REFUND',
                description=f"Withdrawal failed reversal: {instance.order_reference}",
                metadata={'failed_payout_id': instance.id}
            )
