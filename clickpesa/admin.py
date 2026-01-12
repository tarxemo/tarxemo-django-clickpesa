"""
Django admin configuration for ClickPesa payment models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import AuthToken, PaymentTransaction, PayoutTransaction


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    """Admin interface for authentication tokens."""
    
    list_display = ['id', 'created_at', 'expires_at', 'is_active', 'is_valid_status']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['token', 'created_at', 'expires_at', 'is_active']
    ordering = ['-created_at']
    
    def is_valid_status(self, obj):
        """Display token validity status with color."""
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual token creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable token deletion."""
        return False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """Admin interface for payment transactions."""
    
    list_display = [
        'order_reference', 'status_badge', 'collected_amount', 
        'collected_currency', 'customer_phone', 'channel_provider', 
        'created_at'
    ]
    list_filter = ['status', 'channel', 'collected_currency', 'created_at']
    search_fields = ['order_reference', 'id', 'customer_phone', 'customer_name', 'customer_email']
    readonly_fields = [
        'id', 'order_reference', 'payment_reference', 'status', 'channel',
        'channel_provider', 'collected_amount', 'collected_currency',
        'customer_name', 'customer_phone', 'customer_email', 'message',
        'raw_response', 'created_at', 'updated_at', 'completed_at', 'user'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('id', 'order_reference', 'payment_reference', 'status')
        }),
        ('Payment Details', {
            'fields': ('channel', 'channel_provider', 'collected_amount', 'collected_currency')
        }),
        ('Customer Info', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'user')
        }),
        ('Additional Info', {
            'fields': ('message', 'raw_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'SUCCESS': 'green',
            'SETTLED': 'green',
            'PROCESSING': 'orange',
            'PENDING': 'orange',
            'FAILED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual payment creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable payment deletion."""
        return False
    
    actions = ['refresh_status']
    
    def refresh_status(self, request, queryset):
        """Refresh payment status from API."""
        from .managers.payment_manager import PaymentManager
        
        manager = PaymentManager()
        updated = 0
        
        for payment in queryset:
            if payment.is_pending():
                try:
                    manager.check_payment_status(payment.order_reference)
                    updated += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f"Failed to refresh {payment.order_reference}: {str(e)}",
                        level='error'
                    )
        
        self.message_user(request, f"Successfully refreshed {updated} payment(s)")
    refresh_status.short_description = "Refresh payment status"


@admin.register(PayoutTransaction)
class PayoutTransactionAdmin(admin.ModelAdmin):
    """Admin interface for payout transactions."""
    
    list_display = [
        'order_reference', 'status_badge', 'amount', 'currency',
        'fee', 'beneficiary_account_number', 'channel_provider',
        'created_at'
    ]
    list_filter = ['status', 'channel', 'currency', 'exchanged', 'created_at']
    search_fields = [
        'order_reference', 'id', 'beneficiary_account_number',
        'beneficiary_account_name', 'beneficiary_email'
    ]
    readonly_fields = [
        'id', 'order_reference', 'status', 'channel', 'channel_provider',
        'transfer_type', 'amount', 'currency', 'fee', 'beneficiary_amount',
        'exchanged', 'source_currency', 'target_currency', 'source_amount',
        'exchange_rate', 'beneficiary_account_number', 'beneficiary_account_name',
        'beneficiary_mobile_number', 'beneficiary_email', 'beneficiary_swift_number',
        'beneficiary_routing_number', 'notes', 'raw_response', 'created_at',
        'updated_at', 'completed_at', 'user'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('id', 'order_reference', 'status', 'channel', 'channel_provider', 'transfer_type')
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'fee', 'beneficiary_amount')
        }),
        ('Exchange Details', {
            'fields': ('exchanged', 'source_currency', 'target_currency', 'source_amount', 'exchange_rate'),
            'classes': ('collapse',)
        }),
        ('Beneficiary Info', {
            'fields': (
                'beneficiary_account_number', 'beneficiary_account_name',
                'beneficiary_mobile_number', 'beneficiary_email',
                'beneficiary_swift_number', 'beneficiary_routing_number'
            )
        }),
        ('Additional Info', {
            'fields': ('notes', 'user', 'raw_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'SUCCESS': 'green',
            'AUTHORIZED': 'blue',
            'PROCESSING': 'orange',
            'PENDING': 'orange',
            'FAILED': 'red',
            'REVERSED': 'purple',
            'REFUNDED': 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual payout creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable payout deletion."""
        return False
    
    actions = ['refresh_status']
    
    def refresh_status(self, request, queryset):
        """Refresh payout status from API."""
        from .managers.payout_manager import PayoutManager
        
        manager = PayoutManager()
        updated = 0
        
        for payout in queryset:
            if payout.is_pending():
                try:
                    manager.check_payout_status(payout.order_reference)
                    updated += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f"Failed to refresh {payout.order_reference}: {str(e)}",
                        level='error'
                    )
        
        self.message_user(request, f"Successfully refreshed {updated} payout(s)")
    refresh_status.short_description = "Refresh payout status"
