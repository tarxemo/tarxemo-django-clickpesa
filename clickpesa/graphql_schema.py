import graphene
from clickpesa.graphql_types import (
    WalletSingleDTO, WalletTransactionListDTO, EscrowTransactionListDTO,
    WalletType, WalletTransactionType, WalletTransactionSingleDTO
)
from clickpesa.managers.payment_manager import PaymentManager
from clickpesa.models import Wallet, WalletTransaction, EscrowTransaction, PaymentTransaction
from clickpesa.managers.wallet_manager import WalletManager
from tarxemo_django_graphene_utils import build_success_response, build_error_response
from django.core.paginator import Paginator
from django.db import transaction
from clickpesa.managers.payout_manager import PayoutManager
from clickpesa.exceptions import InsufficientBalanceError, PayoutError
import uuid
import logging

logger = logging.getLogger(__name__)

class WalletQuery(graphene.ObjectType):
    my_wallet = graphene.Field(WalletSingleDTO)
    my_wallet_transactions = graphene.Field(
        WalletTransactionListDTO,
        page_number=graphene.Int(),
        items_per_page=graphene.Int(),
        transaction_type=graphene.String(),
        status=graphene.String(),
    )
    my_escrow_transactions = graphene.Field(
        EscrowTransactionListDTO,
        page_number=graphene.Int(),
        items_per_page=graphene.Int(),
        status=graphene.String(),
    )

    def resolve_my_wallet(self, info):
        user = info.context.user
        if not user.is_authenticated:
            return WalletSingleDTO(response=build_error_response("Authentication required"), data=None)
        
        wallet = Wallet.objects.filter(user=user).first()
        if not wallet:
            wm = WalletManager()
            wallet = wm.get_or_create_wallet(user)
            
        return WalletSingleDTO(response=build_success_response(), data=wallet)

    def resolve_my_wallet_transactions(self, info, page_number=1, items_per_page=20, transaction_type=None, status=None):
        user = info.context.user
        if not user.is_authenticated:
            return WalletTransactionListDTO(response=build_error_response("Authentication required"), data=[])
        
        wallet = Wallet.objects.filter(user=user).first()
        if not wallet:
            return WalletTransactionListDTO(response=build_success_response(), data=[])
            
        qs = WalletTransaction.objects.filter(wallet=wallet)
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)
        if status:
            qs = qs.filter(status=status)
            
        paginator = Paginator(qs, items_per_page)
        page_obj = paginator.get_page(page_number)
        
        return WalletTransactionListDTO(response=build_success_response(), data=page_obj.object_list)

    def resolve_my_escrow_transactions(self, info, page_number=1, items_per_page=20, status=None):
        user = info.context.user
        if not user.is_authenticated:
            return EscrowTransactionListDTO(response=build_error_response("Authentication required"), data=[])
        
        # Generic escrow query: find escrows where user is associated with the source object
        # This is a bit tricky for a library. We'll stick to a simple query for now.
        # Projects can override this if they have complex escrow ownership logic.
        qs = EscrowTransaction.objects.all() # Placeholder
        
        if status:
            qs = qs.filter(status=status)
            
        paginator = Paginator(qs, items_per_page)
        page_obj = paginator.get_page(page_number)
        
        return EscrowTransactionListDTO(response=build_success_response(), data=page_obj.object_list)

class WithdrawToMobileMoney(graphene.Mutation):
    """
    Withdraw funds from wallet to mobile money account.
    """
    class Arguments:
        amount = graphene.Decimal(required=True)
        phone_number = graphene.String(required=True)
        channel = graphene.String()

    # We return a single transaction or the updated wallet
    Output = WalletTransactionSingleDTO

    @staticmethod
    def mutate(root, info, amount, phone_number, channel=None):
        user = info.context.user
        if not user.is_authenticated:
            return WalletTransactionSingleDTO(response=build_error_response("Authentication required"), data=None)
        
        try:
            # Format phone
            phone_number = phone_number.replace('+', '').strip()
            
            # Get wallet
            wallet = Wallet.objects.filter(user=user).first()
            if not wallet:
                return WalletTransactionSingleDTO(response=build_error_response("Wallet not found"), data=None)

            if amount <= 0:
                return WalletTransactionSingleDTO(response=build_error_response("Amount must be > 0"), data=None)

            if wallet.balance < amount:
                return WalletTransactionSingleDTO(response=build_error_response(f"Insufficient balance: {wallet.balance}"), data=None)

            wm = WalletManager()
            pm = PayoutManager()

            with transaction.atomic():
                # 1. Create a placeholder transaction and deduct balance
                # Note: reference is generated in save() if not provided
                txn = wm.withdraw(
                    wallet=wallet,
                    amount=amount,
                    description=f"Withdrawal to {phone_number}",
                    metadata={'phone_number': phone_number, 'channel': channel}
                )

                # 2. Initiate payout via manager
                payout = pm.create_payout(
                    amount=float(amount),
                    phone_number=phone_number,
                    order_reference=txn.reference,
                    currency=wallet.currency,
                    preview_first=True,
                    user=user,
                    channel=channel
                )

                # 3. Link payout to transaction
                txn.clickpesa_payout = payout
                txn.status = 'PENDING'
                txn.save(update_fields=['clickpesa_payout', 'status'])

            return WalletTransactionSingleDTO(
                response=build_success_response("Withdrawal initiated successfully"),
                data=txn
            )

        except Exception as e:
            logger.error(f"Withdrawal failed: {str(e)}")
            return WalletTransactionSingleDTO(response=build_error_response(str(e)), data=None)

class InitiateWalletDeposit(graphene.Mutation):
    """
    Initiate a mobile money payment to deposit funds into the wallet.
    """
    class Arguments:
        amount = graphene.Decimal(required=True)
        phone_number = graphene.String(required=True)
    
    # Return the payment transaction details
    # We'll use a generic response structure or return the payment ID/Reference
    class Output(graphene.ObjectType):
        response = graphene.Field("tarxemo_django_graphene_utils.BaseResponseDTO")
        payment_reference = graphene.String()
        order_reference = graphene.String()

    @staticmethod
    def mutate(root, info, amount, phone_number):
        user = info.context.user
        if not user.is_authenticated:
            from tarxemo_django_graphene_utils import BaseResponseDTO
            return InitiateWalletDeposit.Output(
                response=BaseResponseDTO(success=False, message="Authentication required"),
                payment_reference=None,
                order_reference=None
            )
        
        try:
            # Format phone
            phone_number = phone_number.replace('+', '').strip()
            
            pm = PaymentManager()
            
            # Generate unique reference
            user_suffix = str(user.id).replace('-', '')[-6:]
            order_reference = f"WDEP{user_suffix}{uuid.uuid4().hex[:8].upper()}"
            
            # Create payment with metadata
            payment = pm.create_payment(
                amount=float(amount),
                phone_number=phone_number,
                order_reference=order_reference,
                currency=Wallet.objects.filter(user=user).first().currency if hasattr(user, 'clickpesa_wallet') else 'TZS',
                preview_first=False, # Direct initiation for better UX
                user=user,
                metadata={'transaction_type': 'WALLET_DEPOSIT'}
            )
            
            from tarxemo_django_graphene_utils import BaseResponseDTO
            return InitiateWalletDeposit.Output(
                response=BaseResponseDTO(success=True, message="Deposit initiated. Please check your phone."),
                payment_reference=payment.id,
                order_reference=payment.order_reference
            )
            
        except Exception as e:
            from tarxemo_django_graphene_utils import BaseResponseDTO
            return InitiateWalletDeposit.Output(
                response=BaseResponseDTO(success=False, message=str(e)),
                payment_reference=None,
                order_reference=None
            )

class WalletMutations(graphene.ObjectType):
    withdraw_to_mobile_money = WithdrawToMobileMoney.Field()
    initiate_wallet_deposit = InitiateWalletDeposit.Field()
