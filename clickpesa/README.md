# ClickPesa Payment Utility for Django

A modular, reusable Django utility for integrating ClickPesa mobile money payments and payouts into your Django applications.

## Features

- ✅ **Mobile Money Payments** (USSD-PUSH)
  - Preview payment with fees and available methods
  - Initiate payment requests
  - Query payment status
  
- ✅ **Mobile Money Payouts**
  - Preview payout with fees and exchange rates
  - Create payouts to mobile wallets
  - Query payout status
  
- ✅ **Account Management**
  - Check account balance
  
- ✅ **Authentication**
  - Automatic token generation and caching
  - Token refresh management
  
- ✅ **Database Integration**
  - Track all transactions
  - Django admin interface
  - Status updates
  
- ✅ **Modular Architecture**
  - Separate services for each operation
  - Easy to extend for bank payments
  - Reusable across projects

## Installation

### 1. Add to INSTALLED_APPS

Add `clickpesa` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'clickpesa',
]
```

### 2. Configure Settings

Add ClickPesa configuration to your `settings.py` or `.env` file:

```python
# ClickPesa Configuration
CLICKPESA_API_BASE_URL = 'https://api.clickpesa.com'
CLICPESA_API_KEY = 'your-api-key'
CLICPESA_CLIENT_ID = 'your-client-id'
CLICKPESA_CHECKSUM_SECRET = 'your-checksum-secret'  # Optional
DEFAULT_CURRENCY = 'TZS'

# Optional: Webhook configuration
CLICKPESA_WEBHOOK_VERIFY_IPS = ['ip1', 'ip2']
```

### 3. Run Migrations

```bash
python manage.py makemigrations clickpesa
python manage.py migrate clickpesa
```

## Usage

### Simple Payment Example

```python
from clickpesa.managers.payment_manager import PaymentManager

# Create payment manager
payment_mgr = PaymentManager()

# Create a payment
payment = payment_mgr.create_payment(
    amount=10000,  # TZS 10,000
    phone_number="255712345678",
    order_reference="BOOKING-12345",
    currency="TZS",
    preview_first=True  # Preview before initiating
)

print(f"Payment Status: {payment.status}")
print(f"Transaction ID: {payment.id}")

# Check status later
updated_payment = payment_mgr.check_payment_status("BOOKING-12345")
print(f"Current Status: {updated_payment.status}")
```

### Simple Payout Example

```python
from clickpesa.managers.payout_manager import PayoutManager

# Create payout manager
payout_mgr = PayoutManager()

# Create a payout
payout = payout_mgr.create_payout(
    amount=5000,  # TZS 5,000
    phone_number="255712345678",
    order_reference="REFUND-12345",
    currency="TZS",
    preview_first=True
)

print(f"Payout Status: {payout.status}")
print(f"Fee: {payout.fee}")
print(f"Beneficiary Receives: {payout.beneficiary_amount}")
```

### Check Account Balance

```python
from clickpesa.services.account_service import AccountService

service = AccountService()
balance = service.get_account_balance()

print(f"Balance: {balance['currency']} {balance['balance']}")
```

### Preview Payment (Without Initiating)

```python
from clickpesa.services.payment_service import PaymentService

service = PaymentService()

# Preview to see available methods and fees
preview = service.preview_ussd_push(
    amount=10000,
    currency="TZS",
    order_reference="TEST-123",
    phone_number="255712345678",
    fetch_sender_details=True
)

# Check available payment methods
for method in preview['activeMethods']:
    print(f"{method['name']}: {method['status']}")
    if method['status'] == 'AVAILABLE':
        print(f"  Fee: {method['fee']}")
```

## Management Commands

### Test Payment

```bash
# Preview payment
python manage.py test_clickpesa_payment \
    --phone 255712345678 \
    --amount 1000 \
    --preview \
    --check-balance

# Create actual payment
python manage.py test_clickpesa_payment \
    --phone 255712345678 \
    --amount 1000 \
    --reference BOOKING-123
```

### Test Payout

```bash
# Preview payout
python manage.py test_clickpesa_payout \
    --phone 255712345678 \
    --amount 500 \
    --preview \
    --check-balance

# Create actual payout
python manage.py test_clickpesa_payout \
    --phone 255712345678 \
    --amount 500 \
    --reference REFUND-123
```

## Django Admin

Access the Django admin to view and manage transactions:

- **Payment Transactions**: `/admin/clickpesa/paymenttransaction/`
- **Payout Transactions**: `/admin/clickpesa/payouttransaction/`
- **Auth Tokens**: `/admin/clickpesa/authtoken/`

### Admin Features

- View all transactions with color-coded status badges
- Search by order reference, phone number, customer name
- Filter by status, channel, currency, date
- Refresh status action for pending transactions
- Read-only fields for security

## Architecture

### Modular Design

```
clickpesa/
├── services/          # Low-level API operations
│   ├── auth_service.py
│   ├── payment_service.py
│   ├── payout_service.py
│   └── account_service.py
│
├── managers/          # High-level orchestration
│   ├── payment_manager.py
│   └── payout_manager.py
│
├── utils/             # Utilities
│   ├── http_client.py
│   ├── validators.py
│   ├── formatters.py
│   └── checksum.py
│
├── models.py          # Database models
├── admin.py           # Django admin
└── exceptions.py      # Custom exceptions
```

### Service Layer

- **AuthService**: Token generation and caching
- **PaymentService**: Payment operations (preview, initiate, query)
- **PayoutService**: Payout operations (preview, create, query)
- **AccountService**: Account balance retrieval

### Manager Layer

- **PaymentManager**: High-level payment workflow orchestration
- **PayoutManager**: High-level payout workflow orchestration

Managers handle:
- Database record creation
- Status updates
- Error handling
- Transaction management

## Phone Number Format

Phone numbers must be in international format without the `+` sign:

- ✅ Correct: `255712345678`
- ❌ Wrong: `+255712345678`
- ❌ Wrong: `0712345678`

The utility automatically formats phone numbers, but it's best to provide them in the correct format.

## Order Reference Format

Order references must be:
- Unique across all transactions
- Alphanumeric with hyphens and underscores only
- Maximum 100 characters
- Examples: `BOOKING-12345`, `ORDER_ABC123`, `REFUND-2024-001`

## Error Handling

The utility provides specific exceptions for different error types:

```python
from clickpesa.exceptions import (
    PaymentError,
    PayoutError,
    ValidationError,
    AuthenticationError,
    InsufficientBalanceError,
    DuplicateOrderReferenceError
)

try:
    payment = payment_mgr.create_payment(...)
except DuplicateOrderReferenceError:
    # Handle duplicate order
    pass
except ValidationError as e:
    # Handle validation error
    print(f"Validation failed: {e.message}")
except PaymentError as e:
    # Handle payment error
    print(f"Payment failed: {e.message}")
```

## Payment Status Flow

```
PROCESSING → SUCCESS/SETTLED (successful)
          → FAILED (failed)
          → PENDING (awaiting customer action)
```

## Payout Status Flow

```
AUTHORIZED → PROCESSING → SUCCESS (successful)
                       → FAILED (failed)
                       → REVERSED/REFUNDED (reversed)
```

## Expandability

### Adding Bank Payments

The modular design makes it easy to add bank payments:

1. Create `services/bank_payment_service.py`
2. Create `managers/bank_payment_manager.py`
3. Add bank-specific models
4. No changes to existing payment code needed

### Adding Webhooks

To add webhook support:

1. Create `webhooks/` module
2. Add webhook handlers
3. Use `utils/checksum.py` for signature verification
4. Update models to handle webhook events

## Best Practices

1. **Always Preview First**: Use `preview_first=True` to validate before initiating
2. **Check Balance**: Check account balance before payouts
3. **Unique References**: Always use unique order references
4. **Status Monitoring**: Regularly check status for pending transactions
5. **Error Handling**: Always wrap API calls in try-except blocks
6. **Logging**: Enable logging to track API interactions

## Logging

Enable logging to see detailed API interactions:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'clickpesa': {
            'handlers': ['console'],
            'level': 'INFO',  # or 'DEBUG' for more details
        },
    },
}
```

## Security

- API keys are loaded from Django settings
- Tokens are cached securely in database
- All sensitive data is logged with sanitization
- Webhook signature verification supported
- Read-only admin fields prevent accidental modifications

## Support

For issues or questions:
1. Check the ClickPesa API documentation
2. Review the code documentation
3. Check Django logs for detailed error messages

## License

This utility is part of the Bhumwi Enterprises project.
