import logging
from decimal import Decimal
from typing import Optional, Any
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from clickpesa.models import Wallet, WalletTransaction, EscrowTransaction

logger = logging.getLogger(__name__)

class WalletManager:
    """
    Manager for wallet-related operations in ClickPesa library.
    """

    @staticmethod
    def get_or_create_wallet(user) -> Wallet:
        """Get or create a wallet for a user."""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={
                'currency': getattr(settings, 'DEFAULT_CURRENCY', 'TZS'),
                'is_active': True
            }
        )
        return wallet

    @transaction.atomic
    def deposit(
        self, 
        wallet: Wallet, 
        amount: Decimal, 
        transaction_type: str = 'DEPOSIT',
        description: str = "",
        reference: Optional[str] = None,
        related_object: Optional[Any] = None,
        clickpesa_payment: Optional[Any] = None,
        metadata: Optional[dict] = None
    ) -> WalletTransaction:
        """Deposit funds into a wallet."""
        balance_before = wallet.balance
        wallet.balance += amount
        wallet.total_earned += amount
        wallet.last_transaction_at = timezone.now()
        wallet.save(update_fields=['balance', 'total_earned', 'last_transaction_at'])

        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            currency=wallet.currency,
            status='COMPLETED',
            reference=reference,
            description=description,
            balance_before=balance_before,
            balance_after=wallet.balance,
            related_object=related_object,
            clickpesa_payment=clickpesa_payment,
            metadata=metadata or {},
            completed_at=timezone.now()
        )
        return txn

    @transaction.atomic
    def withdraw(
        self, 
        wallet: Wallet, 
        amount: Decimal, 
        transaction_type: str = 'WITHDRAWAL',
        description: str = "",
        reference: Optional[str] = None,
        related_object: Optional[Any] = None,
        clickpesa_payout: Optional[Any] = None,
        metadata: Optional[dict] = None
    ) -> WalletTransaction:
        """Deduct funds from a wallet (e.g. for withdrawal or payment)."""
        if wallet.balance < amount:
            raise ValueError(f"Insufficient funds: {wallet.balance} < {amount}")

        balance_before = wallet.balance
        wallet.balance -= amount
        # total_spent is only updated on actual purchases, for withdrawals we just track balance
        if transaction_type != 'WITHDRAWAL':
            wallet.total_spent += amount
            
        wallet.last_transaction_at = timezone.now()
        wallet.save(update_fields=['balance', 'total_spent', 'last_transaction_at'])

        txn = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            currency=wallet.currency,
            status='PENDING' if clickpesa_payout else 'COMPLETED',
            reference=reference,
            description=description,
            balance_before=balance_before,
            balance_after=wallet.balance,
            related_object=related_object,
            clickpesa_payout=clickpesa_payout,
            metadata=metadata or {},
            completed_at=None if clickpesa_payout else timezone.now()
        )
        return txn

    @transaction.atomic
    def hold_escrow(
        self,
        source_object: Any,
        amount: Decimal,
        platform_fee: Decimal = Decimal('0.00'),
        metadata: Optional[dict] = None
    ) -> EscrowTransaction:
        """
        Create an escrow hold for a source object (e.g. Order).
        Does NOT deduct from buyer wallet here (usually happens via ClickPesa payment signal).
        """
        escrow, created = EscrowTransaction.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(source_object),
            object_id=str(source_object.id),
            defaults={
                'amount': amount,
                'status': 'HELD',
                'platform_fee': platform_fee,
                'seller_receives': amount - platform_fee,
                'metadata': metadata or {}
            }
        )
        return escrow

    @transaction.atomic
    def release_escrow(
        self,
        escrow: EscrowTransaction,
        seller_user: Any,
        trigger: str = 'AUTO_RELEASE'
    ) -> WalletTransaction:
        """Release escrow funds to the seller's wallet."""
        if escrow.status != 'HELD':
            raise ValueError(f"Escrow cannot be released from status: {escrow.status}")

        wallet = self.get_or_create_wallet(seller_user)
        
        # Add funds to seller wallet
        txn = self.deposit(
            wallet=wallet,
            amount=escrow.seller_receives,
            transaction_type='ESCROW_RELEASE',
            description=f"Escrow release for {escrow.source_object}",
            related_object=escrow.source_object,
            metadata={'escrow_id': escrow.id, 'trigger': trigger}
        )

        escrow.status = 'RELEASED'
        escrow.released_at = timezone.now()
        escrow.release_trigger = trigger
        escrow.save(update_fields=['status', 'released_at', 'release_trigger'])
        
        return txn

    @classmethod
    def reconcile_pending_escrows(cls) -> int:
        """
        Scan and release escrows that are past their auto-release date.
        Returns the number of successfully released escrows.
        """
        now = timezone.now()
        pending = EscrowTransaction.objects.filter(
            status='HELD',
            auto_release_date__lte=now
        )
        
        counts = 0
        wm = cls()
        for escrow in pending:
            try:
                # Resolve seller from source object
                obj = escrow.source_object
                seller = None
                
                # Dynamic resolution attempt
                if hasattr(obj, 'get_seller'):
                    seller = obj.get_seller()
                elif hasattr(obj, 'items'):
                    # Likely an order
                    first_item = obj.items.first()
                    if first_item and hasattr(first_item, 'product'):
                        seller = getattr(first_item.product.store, 'created_by', None)
                
                if seller:
                    wm.release_escrow(escrow, seller_user=seller, trigger='AUTO_RELEASE')
                    counts += 1
                else:
                    logger.warning(f"Could not auto-release escrow {escrow.id}: Seller not resolved")
                    
            except Exception as e:
                logger.error(f"Error auto-releasing escrow {escrow.id}: {str(e)}")
        
        return counts
