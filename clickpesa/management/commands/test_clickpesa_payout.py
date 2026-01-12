"""
Management command to test ClickPesa payout functionality.
"""

from django.core.management.base import BaseCommand, CommandError
from clickpesa.managers.payout_manager import PayoutManager
from clickpesa.services.account_service import AccountService
from clickpesa.utils.formatters import format_currency
import uuid


class Command(BaseCommand):
    help = 'Test ClickPesa payout functionality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Beneficiary phone number (e.g., 255712345678)'
        )
        parser.add_argument(
            '--amount',
            type=float,
            required=True,
            help='Payout amount'
        )
        parser.add_argument(
            '--currency',
            type=str,
            default='TZS',
            help='Source currency code (default: TZS)'
        )
        parser.add_argument(
            '--reference',
            type=str,
            help='Order reference (auto-generated if not provided)'
        )
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Only preview payout without creating'
        )
        parser.add_argument(
            '--check-balance',
            action='store_true',
            help='Check account balance before payout'
        )
    
    def handle(self, *args, **options):
        phone = options['phone']
        amount = options['amount']
        currency = options['currency']
        reference = options.get('reference') or f"PAYOUT-{uuid.uuid4().hex[:8].upper()}"
        preview_only = options['preview']
        check_balance = options['check_balance']
        
        self.stdout.write(self.style.SUCCESS('\n=== ClickPesa Payout Test ===\n'))
        
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
        
        # Create payout manager
        payout_manager = PayoutManager()
        
        try:
            if preview_only:
                # Preview only
                self.stdout.write(f'Previewing payout...')
                self.stdout.write(f'  Phone: {phone}')
                self.stdout.write(f'  Amount: {format_currency(amount, currency)}')
                self.stdout.write(f'  Reference: {reference}\n')
                
                from clickpesa.services.payout_service import PayoutService
                service = PayoutService()
                
                preview = service.preview_mobile_money_payout(
                    amount=amount,
                    phone_number=phone,
                    currency=currency,
                    order_reference=reference
                )
                
                # Display preview details
                self.stdout.write(self.style.SUCCESS('\nPayout Preview:'))
                self.stdout.write(f"  Provider: {preview.get('channelProvider')}")
                self.stdout.write(f"  Fee: {format_currency(preview.get('fee', 0), currency)}")
                self.stdout.write(f"  Total Deducted: {format_currency(preview.get('amount', 0), currency)}")
                
                # Display receiver details
                receiver = preview.get('receiver', {})
                if receiver:
                    self.stdout.write(self.style.SUCCESS('\nReceiver Details:'))
                    self.stdout.write(f"  Name: {receiver.get('accountName')}")
                    self.stdout.write(f"  Number: {receiver.get('accountNumber')}")
                    self.stdout.write(f"  Will Receive: {format_currency(receiver.get('amount', 0), receiver.get('accountCurrency', 'TZS'))}")
                
                # Display exchange details if applicable
                if preview.get('exchanged'):
                    exchange = preview.get('exchange', {})
                    self.stdout.write(self.style.SUCCESS('\nExchange Details:'))
                    self.stdout.write(f"  From: {exchange.get('sourceCurrency')} {exchange.get('sourceAmount')}")
                    self.stdout.write(f"  To: {exchange.get('targetCurrency')}")
                    self.stdout.write(f"  Rate: {exchange.get('rate')}")
                
                # Display balance info
                self.stdout.write(self.style.SUCCESS('\nAccount Info:'))
                self.stdout.write(f"  Current Balance: {format_currency(preview.get('balance', 0), currency)}")
                self.stdout.write(f"  After Payout: {format_currency(preview.get('balance', 0) - preview.get('amount', 0), currency)}")
                
                self.stdout.write(self.style.SUCCESS('\n✓ Preview completed successfully'))
            
            else:
                # Create actual payout
                self.stdout.write(f'Creating payout...')
                self.stdout.write(f'  Phone: {phone}')
                self.stdout.write(f'  Amount: {format_currency(amount, currency)}')
                self.stdout.write(f'  Reference: {reference}\n')
                
                payout = payout_manager.create_payout(
                    amount=amount,
                    phone_number=phone,
                    order_reference=reference,
                    currency=currency,
                    preview_first=True
                )
                
                self.stdout.write(self.style.SUCCESS('\n✓ Payout created successfully!'))
                self.stdout.write(f'  Payout ID: {payout.id}')
                self.stdout.write(f'  Order Reference: {payout.order_reference}')
                self.stdout.write(f'  Status: {payout.status}')
                self.stdout.write(f'  Channel: {payout.channel_provider or payout.channel}')
                self.stdout.write(f'  Amount Deducted: {format_currency(payout.amount, payout.currency)}')
                self.stdout.write(f'  Fee: {format_currency(payout.fee, payout.currency)}')
                self.stdout.write(f'  Beneficiary Receives: {format_currency(payout.beneficiary_amount, payout.currency)}')
                
                if payout.exchanged:
                    self.stdout.write(self.style.WARNING(
                        f'\nCurrency Exchange Applied: {payout.source_currency} → {payout.target_currency} @ {payout.exchange_rate}'
                    ))
                
                self.stdout.write(self.style.WARNING(
                    '\nNote: Payout is being processed. Beneficiary should receive funds shortly.'
                ))
                self.stdout.write(
                    f'\nTo check status later, run:\n'
                    f'  python manage.py test_clickpesa_payout --reference {reference} --status-only'
                )
        
        except Exception as e:
            raise CommandError(f'Payout test failed: {str(e)}')
