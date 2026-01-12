"""
Management command to test ClickPesa payment functionality.
"""

from django.core.management.base import BaseCommand, CommandError
from clickpesa.managers.payment_manager import PaymentManager
from clickpesa.services.account_service import AccountService
from clickpesa.utils.formatters import format_currency
import uuid


class Command(BaseCommand):
    help = 'Test ClickPesa payment functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Customer phone number (e.g., 255712345678)'
        )
        parser.add_argument(
            '--amount',
            type=float,
            required=True,
            help='Payment amount'
        )
        parser.add_argument(
            '--currency',
            type=str,
            default='TZS',
            help='Currency code (default: TZS)'
        )
        parser.add_argument(
            '--reference',
            type=str,
            help='Order reference (auto-generated if not provided)'
        )
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Only preview payment without initiating'
        )
        parser.add_argument(
            '--check-balance',
            action='store_true',
            help='Check account balance before payment'
        )
    
    def handle(self, *args, **options):
        phone = options['phone']
        amount = options['amount']
        currency = options['currency']
        reference = options.get('reference') or f"TEST-{uuid.uuid4().hex[:8].upper()}"
        preview_only = options['preview']
        check_balance = options['check_balance']
        
        self.stdout.write(self.style.SUCCESS('\n=== ClickPesa Payment Test ===\n'))
        
        # Check balance if requested
        if check_balance:
            try:
                self.stdout.write('Checking account balance...')
                account_service = AccountService()
                balance_data = account_service.get_account_balance()
                
                self.stdout.write(self.style.SUCCESS(
                    f"Account Balance: {format_currency(balance_data['balance'], balance_data['currency'])}\n"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to check balance: {str(e)}\n"))
        
        # Create payment manager
        payment_manager = PaymentManager()
        
        try:
            if preview_only:
                # Preview only
                self.stdout.write(f'Previewing payment...')
                self.stdout.write(f'  Phone: {phone}')
                self.stdout.write(f'  Amount: {format_currency(amount, currency)}')
                self.stdout.write(f'  Reference: {reference}\n')
                
                from clickpesa.services.payment_service import PaymentService
                service = PaymentService()
                
                preview = service.preview_ussd_push(
                    amount=amount,
                    currency=currency,
                    order_reference=reference,
                    phone_number=phone,
                    fetch_sender_details=True
                )
                
                # Display available methods
                self.stdout.write(self.style.SUCCESS('\nAvailable Payment Methods:'))
                for method in preview.get('activeMethods', []):
                    status_style = self.style.SUCCESS if method['status'] == 'AVAILABLE' else self.style.WARNING
                    self.stdout.write(
                        f"  - {method['name']}: {status_style(method['status'])}"
                    )
                    if method['status'] == 'AVAILABLE':
                        self.stdout.write(f"    Fee: {format_currency(method.get('fee', 0), currency)}")
                
                # Display sender details if available
                sender = preview.get('sender')
                if sender:
                    self.stdout.write(self.style.SUCCESS('\nSender Details:'))
                    self.stdout.write(f"  Name: {sender.get('accountName')}")
                    self.stdout.write(f"  Number: {sender.get('accountNumber')}")
                    self.stdout.write(f"  Provider: {sender.get('accountProvider')}")
                
                self.stdout.write(self.style.SUCCESS('\n✓ Preview completed successfully'))
            
            else:
                # Create actual payment
                self.stdout.write(f'Creating payment...')
                self.stdout.write(f'  Phone: {phone}')
                self.stdout.write(f'  Amount: {format_currency(amount, currency)}')
                self.stdout.write(f'  Reference: {reference}\n')
                
                payment = payment_manager.create_payment(
                    amount=amount,
                    phone_number=phone,
                    order_reference=reference,
                    currency=currency,
                    preview_first=True
                )
                
                self.stdout.write(self.style.SUCCESS('\n✓ Payment created successfully!'))
                self.stdout.write(f'  Transaction ID: {payment.id}')
                self.stdout.write(f'  Order Reference: {payment.order_reference}')
                self.stdout.write(f'  Status: {payment.status}')
                self.stdout.write(f'  Channel: {payment.channel_provider or payment.channel}')
                self.stdout.write(f'  Amount: {format_currency(payment.collected_amount, payment.collected_currency)}')
                
                self.stdout.write(self.style.WARNING(
                    '\nNote: Customer should receive USSD push on their phone to complete payment.'
                ))
                self.stdout.write(
                    f'\nTo check status later, run:\n'
                    f'  python manage.py test_clickpesa_payment --reference {reference} --status-only'
                )
        
        except Exception as e:
            raise CommandError(f'Payment test failed: {str(e)}')
