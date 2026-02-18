import graphene
from graphene_django import DjangoObjectType
from clickpesa.models import Wallet, WalletTransaction, EscrowTransaction
from tarxemo_django_graphene_utils import BaseResponseDTO

class WalletType(DjangoObjectType):
    """Wallet GraphQL type"""
    balance = graphene.String()
    total_earned = graphene.String()
    total_spent = graphene.String()
    escrow_balance = graphene.String()

    class Meta:
        model = Wallet
        fields = (
            'id', 'user', 'balance', 'currency', 'is_active',
            'total_earned', 'total_spent', 'last_transaction_at',
            'created_at', 'updated_at'
        )

    def resolve_balance(self, info):
        return str(self.balance)

    def resolve_total_earned(self, info):
        return str(self.total_earned)

    def resolve_total_spent(self, info):
        return str(self.total_spent)

    def resolve_escrow_balance(self, info):
        return str(self.get_escrow_balance())


class WalletTransactionType(DjangoObjectType):
    """Wallet transaction GraphQL type"""
    amount = graphene.String()
    balance_before = graphene.String()
    balance_after = graphene.String()
    related_object_id = graphene.String()
    related_object_type = graphene.String()
    related_order_number = graphene.String()

    class Meta:
        model = WalletTransaction
        fields = (
            'id', 'wallet', 'transaction_type', 'amount', 'currency',
            'status', 'reference', 'description', 'metadata',
            'balance_before', 'balance_after', 'created_at', 'completed_at'
        )

    def resolve_amount(self, info):
        return str(self.amount)

    def resolve_balance_before(self, info):
        return str(self.balance_before) if self.balance_before else None

    def resolve_balance_after(self, info):
        return str(self.balance_after) if self.balance_after else None

    def resolve_related_object_id(self, info):
        return str(self.object_id) if self.object_id else None

    def resolve_related_object_type(self, info):
        return str(self.content_type.model) if self.content_type else None

    def resolve_related_order_number(self, info):
        """Try to get order number from related object"""
        obj = self.related_object
        if obj:
            return getattr(obj, 'order_number', None)
        return None


class EscrowTransactionType(DjangoObjectType):
    """Escrow transaction GraphQL type"""
    amount = graphene.String()
    platform_fee = graphene.String()
    seller_receives = graphene.String()
    source_object_id = graphene.String()
    source_object_type = graphene.String()
    order_number = graphene.String()

    class Meta:
        model = EscrowTransaction
        fields = (
            'id', 'amount', 'currency', 'status', 'platform_fee',
            'seller_receives', 'held_at', 'released_at', 'release_trigger',
            'auto_release_date', 'metadata'
        )

    def resolve_amount(self, info):
        return str(self.amount)

    def resolve_platform_fee(self, info):
        return str(self.platform_fee)

    def resolve_seller_receives(self, info):
        return str(self.seller_receives)

    def resolve_source_object_id(self, info):
        return str(self.object_id)

    def resolve_source_object_type(self, info):
        return str(self.content_type.model)

    def resolve_order_number(self, info):
        """Try to get order number from source object"""
        obj = self.source_object
        if obj:
            return getattr(obj, 'order_number', None)
        return None


# DTOs for responses
class WalletSingleDTO(BaseResponseDTO):
    data = graphene.Field(WalletType)

class WalletTransactionSingleDTO(BaseResponseDTO):
    data = graphene.Field(WalletTransactionType)

class WalletTransactionListDTO(BaseResponseDTO):
    data = graphene.List(WalletTransactionType)

class EscrowTransactionListDTO(BaseResponseDTO):
    data = graphene.List(EscrowTransactionType)
