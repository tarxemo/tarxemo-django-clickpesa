from django.core.management.base import BaseCommand
from django.utils import timezone
from clickpesa.models import PaymentTransaction, PayoutTransaction
from clickpesa.managers.payment_manager import PaymentManager
from clickpesa.managers.payout_manager import PayoutManager
from clickpesa.managers.wallet_manager import WalletManager

class Command(BaseCommand):
    help = 'Reconcile pending ClickPesa transactions and process escrow releases'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting ClickPesa reconciliation...'))
        
        # 1. Reconcile Payments
        pending_payments = PaymentTransaction.objects.filter(status__in=['PROCESSING', 'PENDING'])
        self.stdout.write(f"Syncing {pending_payments.count()} pending payments...")
        pm = PaymentManager()
        for txn in pending_payments:
            try:
                pm.check_payment_status(txn.order_reference)
                self.stdout.write(f"  Processed payment: {txn.order_reference}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error syncing {txn.order_reference}: {str(e)}"))

        # 2. Reconcile Payouts
        pending_payouts = PayoutTransaction.objects.filter(status__in=['PROCESSING', 'PENDING', 'AUTHORIZED'])
        self.stdout.write(f"Syncing {pending_payouts.count()} pending payouts...")
        pom = PayoutManager()
        for txn in pending_payouts:
            try:
                pom.check_payout_status(txn.order_reference)
                self.stdout.write(f"  Processed payout: {txn.order_reference}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error syncing {txn.order_reference}: {str(e)}"))

        # 3. Process Auto-release Escrows
        self.stdout.write("Processing auto-release escrows...")
        wm = WalletManager()
        released_count = wm.reconcile_pending_escrows()
        self.stdout.write(self.style.SUCCESS(f"Successfully released {released_count} escrows"))

        self.stdout.write(self.style.SUCCESS('Reconciliation complete!'))
