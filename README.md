# tarxemo-django-clickpesa

A comprehensive Django library for integrating **ClickPesa** mobile money payments and payouts into your applications. This library provides a clean, service-oriented architecture for handling payment transactions, payouts, and account management with full database tracking and Django signals support.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Core Concepts](#core-concepts)
- [API Reference](#api-reference)
- [Signals](#signals)
- [Django Admin](#django-admin)
- [Management Commands](#management-commands)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Features

✅ **Mobile Money Payments (USSD-PUSH)**
- Preview payments with fees and available methods
- Initiate payment requests to customer phones
- Query payment status and track lifecycle
- Support for all major Tanzanian mobile money providers (M-Pesa, Tigo Pesa, Airtel Money, HaloPesa)

✅ **Mobile Money Payouts**
- Preview payouts with fees and exchange rates
- Create B2C payouts to mobile wallets
- Query payout status
- Automatic fee calculation

✅ **Account Management**
- Check account balance
- Multi-currency support (TZS, USD)

✅ **Automatic Authentication**
- Token generation and caching
- Automatic token refresh
- Secure token storage in database

✅ **Database Integration**
- Track all transactions with full audit trail
- Django admin interface for viewing transactions
- Automatic status updates
- Transaction history

✅ **Django Signals**
- `payment_status_changed` - Emitted when payment status changes
- `payout_status_changed` - Emitted when payout status changes
- Decoupled event system for business logic

✅ **Production-Ready**
- Comprehensive error handling
- Input validation
- Logging support
- Retry mechanisms
- Webhook support (checksum verification)

---

## Installation

### From PyPI (Recommended)

```bash
pip install tarxemo-django-clickpesa
```

### From GitHub (Development)

```bash
pip install git+https://github.com/tarxemo/tarxemo-django-clickpesa.git
```

### Dependencies

- **Django** >= 3.2
- **requests** >= 2.25.0

---

## Quick Start

### Step 1: Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ... your other apps
    'clickpesa',
]
```

### Step 2: Configure Settings

Add your ClickPesa credentials to `settings.py`:

```python
# ClickPesa Configuration
CLICKPESA_API_BASE_URL = 'https://api.clickpesa.com'  # Production
# CLICKPESA_API_BASE_URL = 'https://sandbox.clickpesa.com'  # Sandbox for testing

CLICPESA_API_KEY = 'your-api-key-here'
CLICPESA_CLIENT_ID = 'your-client-id-here'

# Optional settings
CLICKPESA_CHECKSUM_SECRET = 'your-webhook-secret'  # For webhook verification
DEFAULT_CURRENCY = 'TZS'
```

**Getting API Credentials:**
1. Sign up at [ClickPesa](https://clickpesa.com)
2. Complete KYC verification
3. Navigate to API Settings in your dashboard
4. Copy your API Key and Client ID
5. Use sandbox credentials for testing

### Step 3: Run Migrations

```bash
python manage.py migrate clickpesa
```

This creates three tables:
- `clickpesa_auth_tokens` - Authentication tokens
- `clickpesa_payment_transactions` - Payment records
- `clickpesa_payout_transactions` - Payout records

### Step 4: Create Your First Payment

```python
from clickpesa.managers.payment_manager import PaymentManager

# Initialize manager
payment_mgr = PaymentManager()

# Create a payment
payment = payment_mgr.create_payment(
    amount=10000,  # TZS 10,000
    phone_number="255712345678",  # International format without +
    order_reference="ORDER-12345",  # Unique reference
    currency="TZS",
    preview_first=True  # Preview before initiating
)

print(f"Payment Status: {payment.status}")
print(f"Transaction ID: {payment.id}")
```

### Step 5: Listen for Status Changes

```python
# In your app's signals.py or models.py
from django.dispatch import receiver
from clickpesa.signals import payment_status_changed

@receiver(payment_status_changed)
def handle_payment_status(sender, instance, new_status, old_status=None, **kwargs):
    """Handle payment status changes"""
    if new_status == 'SUCCESS':
        # Payment successful - fulfill order
        order = Order.objects.get(reference=instance.order_reference)
        order.status = 'paid'
        order.save()
        
        # Send confirmation email
        send_payment_confirmation(order)
    
    elif new_status == 'FAILED':
        # Payment failed - notify user
        notify_payment_failure(instance.order_reference)
```

**That's it!** You now have a working payment system. Continue reading for advanced features.

---

## Configuration

### Required Settings

```python
# API Base URL
CLICKPESA_API_BASE_URL = 'https://api.clickpesa.com'  # Production
# CLICKPESA_API_BASE_URL = 'https://sandbox.clickpesa.com'  # Sandbox

# API Credentials (REQUIRED)
CLICPESA_API_KEY = 'your-api-key'
CLICPESA_CLIENT_ID = 'your-client-id'
```

### Optional Settings

```python
# Webhook Secret for signature verification
CLICKPESA_CHECKSUM_SECRET = 'your-webhook-secret'

# Default currency
DEFAULT_CURRENCY = 'TZS'  # or 'USD'

# Callback URLs
CLICKPESA_SUCCESS_URL = 'https://yoursite.com/payment/success'
CLICKPESA_CANCEL_URL = 'https://yoursite.com/payment/cancel'

# Webhook IP verification
CLICKPESA_WEBHOOK_VERIFY_IPS = ['ip1', 'ip2']
```

### Environment Variables (Recommended)

For security, use environment variables:

```python
# settings.py
import os

CLICPESA_API_KEY = os.getenv('CLICKPESA_API_KEY')
CLICPESA_CLIENT_ID = os.getenv('CLICKPESA_CLIENT_ID')
CLICKPESA_CHECKSUM_SECRET = os.getenv('CLICKPESA_CHECKSUM_SECRET')
```

```bash
# .env file
CLICKPESA_API_KEY=your-api-key
CLICKPESA_CLIENT_ID=your-client-id
CLICKPESA_CHECKSUM_SECRET=your-webhook-secret
```

---

## Core Concepts

### Architecture

The library uses a layered architecture:

```
┌─────────────────────────────────────┐
│         Your Application            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Managers Layer              │  ← High-level API (recommended)
│  - PaymentManager                   │
│  - PayoutManager                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Services Layer              │  ← Low-level API (advanced)
│  - AuthService                      │
│  - PaymentService                   │
│  - PayoutService                    │
│  - AccountService                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         ClickPesa API               │
└─────────────────────────────────────┘
```

**Managers** (High-level):
- Handle complete workflows
- Manage database records
- Emit signals
- Recommended for most use cases

**Services** (Low-level):
- Direct API operations
- No database interaction
- For advanced customization

### Models

#### AuthToken

Stores JWT authentication tokens with automatic caching.

**Fields:**
- `token` - JWT token string
- `created_at` - When token was created
- `is_active` - Whether token is currently valid

**Methods:**
- `is_expired()` - Check if token has expired
- `is_valid()` - Check if token is active and not expired
- `get_valid_token()` - Class method to get a valid token from DB
- `create_token(token_string)` - Class method to create new token

#### PaymentTransaction

Stores payment transaction records.

**Fields:**
- `id` - ClickPesa transaction ID (primary key)
- `order_reference` - Your unique order reference
- `amount` - Payment amount
- `currency` - Currency code (TZS, USD)
- `status` - Payment status (PROCESSING, SUCCESS, FAILED, etc.)
- `customer_phone` - Customer phone number
- `customer_name` - Customer name (from provider)
- `channel` - Payment channel (MOBILE MONEY)
- `provider` - Mobile money provider (M-PESA, TIGO-PESA, etc.)
- `fee` - Transaction fee
- `user` - Associated Django user (optional)
- `created_at`, `updated_at` - Timestamps

**Methods:**
- `is_successful()` - Returns True if payment succeeded
- `is_pending()` - Returns True if payment is pending
- `is_failed()` - Returns True if payment failed

#### PayoutTransaction

Stores payout transaction records.

**Fields:**
- `id` - ClickPesa payout ID (primary key)
- `order_reference` - Your unique order reference
- `amount` - Payout amount
- `currency` - Currency code
- `status` - Payout status (AUTHORIZED, PROCESSING, SUCCESS, etc.)
- `beneficiary_account_number` - Recipient phone number
- `beneficiary_name` - Recipient name
- `beneficiary_amount` - Amount beneficiary receives
- `fee` - Transaction fee
- `exchange_rate` - Exchange rate (if applicable)
- `user` - Associated Django user (optional)
- `created_at`, `updated_at` - Timestamps

**Methods:**
- `is_successful()` - Returns True if payout succeeded
- `is_pending()` - Returns True if payout is pending
- `is_failed()` - Returns True if payout failed
- `is_reversed()` - Returns True if payout was reversed

### Transaction Lifecycle

**Payment Status Flow:**
```
PROCESSING → SUCCESS/SETTLED (payment successful)
          → FAILED (payment failed)
          → PENDING (awaiting customer action)
```

**Payout Status Flow:**
```
AUTHORIZED → PROCESSING → SUCCESS (payout successful)
                       → FAILED (payout failed)
                       → REVERSED/REFUNDED (payout reversed)
```

---

## API Reference

### PaymentManager

High-level manager for payment operations.

#### `create_payment(amount, phone_number, order_reference, currency='TZS', preview_first=True, user=None)`

Create a new payment transaction.

**Parameters:**
- `amount` (float) - Payment amount
- `phone_number` (str) - Customer phone in international format (e.g., "255712345678")
- `order_reference` (str) - Unique order reference (max 100 chars, alphanumeric + hyphens/underscores)
- `currency` (str, optional) - Currency code, default: "TZS"
- `preview_first` (bool, optional) - Preview before initiating, default: True
- `user` (User, optional) - Django user to associate with transaction

**Returns:** `PaymentTransaction` instance

**Raises:**
- `DuplicateOrderReferenceError` - Order reference already exists
- `ValidationError` - Invalid input (phone, amount, etc.)
- `PaymentError` - Payment initiation failed

**Example:**
```python
from clickpesa.managers.payment_manager import PaymentManager

manager = PaymentManager()
payment = manager.create_payment(
    amount=50000,
    phone_number="255712345678",
    order_reference="INV-2024-001",
    currency="TZS",
    preview_first=True,
    user=request.user
)
```

#### `check_payment_status(order_reference)`

Check and update payment status from ClickPesa API.

**Parameters:**
- `order_reference` (str) - Order reference to check

**Returns:** Updated `PaymentTransaction` instance

**Raises:**
- `PaymentError` - Status check failed or payment not found

**Example:**
```python
updated_payment = manager.check_payment_status("INV-2024-001")
print(f"Current status: {updated_payment.status}")
```

#### `get_payment_by_reference(order_reference)`

Get payment transaction by order reference.

**Parameters:**
- `order_reference` (str) - Order reference

**Returns:** `PaymentTransaction` instance or `None`

#### `get_payment_by_id(transaction_id)`

Get payment transaction by ClickPesa transaction ID.

**Parameters:**
- `transaction_id` (str) - ClickPesa transaction ID

**Returns:** `PaymentTransaction` instance or `None`

---

### PayoutManager

High-level manager for payout operations.

#### `create_payout(amount, phone_number, order_reference, currency='TZS', preview_first=True, user=None)`

Create a new payout transaction.

**Parameters:**
- `amount` (float) - Payout amount
- `phone_number` (str) - Beneficiary phone in international format
- `order_reference` (str) - Unique order reference
- `currency` (str, optional) - Currency code, default: "TZS"
- `preview_first` (bool, optional) - Preview before creating, default: True
- `user` (User, optional) - Django user to associate with transaction

**Returns:** `PayoutTransaction` instance

**Raises:**
- `DuplicateOrderReferenceError` - Order reference already exists
- `ValidationError` - Invalid input
- `InsufficientBalanceError` - Account balance too low
- `PayoutError` - Payout creation failed

**Example:**
```python
from clickpesa.managers.payout_manager import PayoutManager

manager = PayoutManager()
payout = manager.create_payout(
    amount=25000,
    phone_number="255712345678",
    order_reference="REFUND-2024-001",
    currency="TZS",
    user=request.user
)
```

#### `check_payout_status(order_reference)`

Check and update payout status.

**Parameters:**
- `order_reference` (str) - Order reference

**Returns:** Updated `PayoutTransaction` instance

#### `get_payout_by_reference(order_reference)`

Get payout by order reference.

#### `get_payout_by_id(transaction_id)`

Get payout by ClickPesa payout ID.

---

### PaymentService (Advanced)

Low-level service for direct payment API operations.

#### `preview_ussd_push(amount, currency, order_reference, phone_number, fetch_sender_details=True)`

Preview a payment to see fees and available methods.

**Returns:** Dict with preview data including fees and active methods

**Example:**
```python
from clickpesa.services.payment_service import PaymentService

service = PaymentService()
preview = service.preview_ussd_push(
    amount=10000,
    currency="TZS",
    order_reference="TEST-001",
    phone_number="255712345678"
)

print(f"Fee: {preview['fee']}")
for method in preview['activeMethods']:
    print(f"{method['name']}: {method['status']}")
```

#### `initiate_ussd_push(amount, currency, order_reference, phone_number)`

Initiate a USSD push payment request.

**Returns:** Dict with transaction details

#### `query_payment_status(order_reference)`

Query payment status from API.

**Returns:** Dict with payment status and details

---

### PayoutService (Advanced)

Low-level service for payout operations.

#### `preview_payout(amount, currency, order_reference, phone_number)`

Preview a payout to see fees and exchange rates.

#### `create_payout(amount, currency, order_reference, phone_number)`

Create a payout transaction.

#### `query_payout_status(order_reference)`

Query payout status from API.

---

### AccountService

Service for account operations.

#### `get_account_balance()`

Get current account balance.

**Returns:** Dict with balance information

**Example:**
```python
from clickpesa.services.account_service import AccountService

service = AccountService()
balance = service.get_account_balance()
print(f"Balance: {balance['currency']} {balance['balance']}")
```

---

## Signals

### payment_status_changed

Emitted when a payment transaction status changes.

**Arguments:**
- `sender` - PaymentTransaction class
- `instance` - PaymentTransaction instance
- `new_status` - New status string
- `old_status` - Previous status string (if updated)
- `created` - Boolean, True if transaction was just created

**Example:**
```python
from django.dispatch import receiver
from clickpesa.signals import payment_status_changed

@receiver(payment_status_changed)
def on_payment_status_change(sender, instance, new_status, old_status=None, created=False, **kwargs):
    if new_status == 'SUCCESS':
        # Fulfill order
        process_successful_payment(instance)
    elif new_status == 'FAILED':
        # Handle failure
        handle_failed_payment(instance)
```

### payout_status_changed

Emitted when a payout transaction status changes.

**Arguments:** Same as `payment_status_changed`

---

## Django Admin

Access at `/admin/clickpesa/` to view and manage transactions.

### Features

- **Color-coded status badges** for quick visual identification
- **Search** by order reference, phone number, customer name
- **Filter** by status, channel, currency, date range
- **Refresh status action** for pending transactions
- **Read-only fields** for security (transaction IDs, amounts, etc.)
- **Detailed view** showing all transaction information

### Admin Actions

**Refresh Status:**
1. Select one or more pending transactions
2. Choose "Refresh status from ClickPesa" from actions dropdown
3. Click "Go"
4. Status will be updated from API

---

## Management Commands

### test_clickpesa_payment

Test payment functionality from command line.

**Usage:**
```bash
# Preview a payment
python manage.py test_clickpesa_payment \
    --phone 255712345678 \
    --amount 1000 \
    --preview \
    --check-balance

# Create actual payment
python manage.py test_clickpesa_payment \
    --phone 255712345678 \
    --amount 1000 \
    --reference TEST-001

# With custom currency
python manage.py test_clickpesa_payment \
    --phone 255712345678 \
    --amount 100 \
    --currency USD \
    --reference TEST-USD-001
```

**Options:**
- `--phone` - Phone number (required)
- `--amount` - Amount (required)
- `--reference` - Order reference (optional, auto-generated if not provided)
- `--currency` - Currency code (default: TZS)
- `--preview` - Preview only, don't initiate
- `--check-balance` - Check account balance before payment

### test_clickpesa_payout

Test payout functionality.

**Usage:**
```bash
# Preview a payout
python manage.py test_clickpesa_payout \
    --phone 255712345678 \
    --amount 500 \
    --preview \
    --check-balance

# Create actual payout
python manage.py test_clickpesa_payout \
    --phone 255712345678 \
    --amount 500 \
    --reference PAYOUT-001
```

---

## Usage Examples

### Example 1: Complete Payment Flow

```python
from clickpesa.managers.payment_manager import PaymentManager
from clickpesa.exceptions import PaymentError, DuplicateOrderReferenceError

def process_order_payment(order):
    """Process payment for an order"""
    manager = PaymentManager()
    
    try:
        payment = manager.create_payment(
            amount=order.total_amount,
            phone_number=order.customer_phone,
            order_reference=f"ORDER-{order.id}",
            currency="TZS",
            preview_first=True,
            user=order.customer
        )
        
        # Update order
        order.payment_transaction_id = payment.id
        order.payment_status = 'processing'
        order.save()
        
        return payment
        
    except DuplicateOrderReferenceError:
        # Payment already initiated
        return manager.get_payment_by_reference(f"ORDER-{order.id}")
    
    except PaymentError as e:
        # Log error and notify admin
        logger.error(f"Payment failed for order {order.id}: {e.message}")
        raise
```

### Example 2: Handling Payment Callbacks

```python
from django.dispatch import receiver
from clickpesa.signals import payment_status_changed
from django.core.mail import send_mail

@receiver(payment_status_changed)
def handle_payment_update(sender, instance, new_status, **kwargs):
    """Handle payment status changes"""
    
    # Get associated order
    order_ref = instance.order_reference
    order = Order.objects.get(reference=order_ref)
    
    if new_status == 'SUCCESS':
        # Mark order as paid
        order.status = 'paid'
        order.paid_at = timezone.now()
        order.save()
        
        # Send confirmation email
        send_mail(
            subject=f'Payment Confirmed - {order_ref}',
            message=f'Your payment of TZS {instance.amount} has been confirmed.',
            from_email='noreply@example.com',
            recipient_list=[order.customer.email],
        )
        
        # Trigger fulfillment
        fulfill_order.delay(order.id)
    
    elif new_status == 'FAILED':
        # Mark order as payment failed
        order.status = 'payment_failed'
        order.save()
        
        # Notify customer
        send_mail(
            subject=f'Payment Failed - {order_ref}',
            message='Your payment failed. Please try again.',
            from_email='noreply@example.com',
            recipient_list=[order.customer.email],
        )
```

### Example 3: Refund/Payout Flow

```python
from clickpesa.managers.payout_manager import PayoutManager
from clickpesa.exceptions import InsufficientBalanceError

def process_refund(order):
    """Process refund as payout"""
    manager = PayoutManager()
    
    try:
        # Check balance first
        from clickpesa.services.account_service import AccountService
        balance_info = AccountService().get_account_balance()
        
        if float(balance_info['balance']) < order.total_amount:
            raise InsufficientBalanceError("Insufficient balance for refund")
        
        # Create payout
        payout = manager.create_payout(
            amount=order.total_amount,
            phone_number=order.customer_phone,
            order_reference=f"REFUND-{order.id}",
            currency="TZS",
            user=order.customer
        )
        
        # Update order
        order.refund_transaction_id = payout.id
        order.refund_status = 'processing'
        order.save()
        
        return payout
        
    except InsufficientBalanceError as e:
        logger.error(f"Insufficient balance for refund: {order.id}")
        raise
```

### Example 4: Checking Payment Before Proceeding

```python
def check_payment_before_delivery(order_id):
    """Check payment status before delivering order"""
    from clickpesa.managers.payment_manager import PaymentManager
    
    order = Order.objects.get(id=order_id)
    manager = PaymentManager()
    
    # Get latest status from API
    payment = manager.check_payment_status(f"ORDER-{order.id}")
    
    if payment.is_successful():
        # Payment confirmed - proceed with delivery
        schedule_delivery(order)
        return True
    elif payment.is_pending():
        # Still waiting
        return False
    else:
        # Payment failed
        cancel_order(order)
        return False
```

---

## Best Practices

### 1. Always Preview Before Initiating

```python
# Good - preview first
payment = manager.create_payment(
    amount=10000,
    phone_number="255712345678",
    order_reference="ORDER-123",
    preview_first=True  # ✓
)

# Risky - no preview
payment = manager.create_payment(
    amount=10000,
    phone_number="255712345678",
    order_reference="ORDER-123",
    preview_first=False  # ✗
)
```

### 2. Check Balance Before Payouts

```python
from clickpesa.services.account_service import AccountService

def safe_payout(amount, phone, reference):
    # Check balance first
    balance = AccountService().get_account_balance()
    
    if float(balance['balance']) < amount:
        raise InsufficientBalanceError("Not enough balance")
    
    # Proceed with payout
    return PayoutManager().create_payout(amount, phone, reference)
```

### 3. Use Unique Order References

```python
import uuid

# Good - guaranteed unique
order_ref = f"ORDER-{uuid.uuid4().hex[:12].upper()}"

# Good - unique per order
order_ref = f"ORDER-{order.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

# Bad - might duplicate
order_ref = "ORDER-123"  # ✗
```

### 4. Handle Exceptions Properly

```python
from clickpesa.exceptions import (
    PaymentError, ValidationError, 
    DuplicateOrderReferenceError, InsufficientBalanceError
)

try:
    payment = manager.create_payment(...)
except DuplicateOrderReferenceError:
    # Order reference exists - retrieve existing payment
    payment = manager.get_payment_by_reference(order_ref)
except ValidationError as e:
    # Invalid input - show error to user
    return JsonResponse({'error': e.message}, status=400)
except InsufficientBalanceError:
    # Not enough balance
    notify_admin("Low balance alert")
    raise
except PaymentError as e:
    # General payment error
    logger.error(f"Payment failed: {e.message}")
    raise
```

### 5. Monitor Transaction Status

```python
from celery import shared_task

@shared_task
def check_pending_payments():
    """Periodic task to check pending payments"""
    from clickpesa.models import PaymentTransaction
    from clickpesa.managers.payment_manager import PaymentManager
    
    manager = PaymentManager()
    
    # Get payments pending for more than 5 minutes
    cutoff = timezone.now() - timedelta(minutes=5)
    pending = PaymentTransaction.objects.filter(
        status='PENDING',
        created_at__lt=cutoff
    )
    
    for payment in pending:
        try:
            manager.check_payment_status(payment.order_reference)
        except Exception as e:
            logger.error(f"Status check failed: {e}")
```

### 6. Use Signals for Business Logic

```python
# Don't do this - tight coupling
def create_payment(order):
    payment = manager.create_payment(...)
    if payment.status == 'SUCCESS':
        order.status = 'paid'
        order.save()
        send_email(order)
        update_inventory(order)
    return payment

# Do this - use signals
def create_payment(order):
    return manager.create_payment(...)

@receiver(payment_status_changed)
def on_payment_success(sender, instance, new_status, **kwargs):
    if new_status == 'SUCCESS':
        order = Order.objects.get(reference=instance.order_reference)
        order.status = 'paid'
        order.save()
        send_email(order)
        update_inventory(order)
```

### 7. Phone Number Format

```python
# Correct format
phone = "255712345678"  # ✓ International format without +

# Incorrect formats
phone = "+255712345678"  # ✗ No + sign
phone = "0712345678"     # ✗ Must include country code
phone = "712345678"      # ✗ Must include country code
```

---

## Troubleshooting

### Issue: "CLICPESA_API_KEY is not configured"

**Cause:** API credentials not set in settings.py

**Solution:**
```python
# Add to settings.py
CLICPESA_API_KEY = 'your-api-key'
CLICPESA_CLIENT_ID = 'your-client-id'
```

### Issue: "Invalid phone number format"

**Cause:** Phone number not in correct format

**Solution:**
```python
# Use international format without +
phone = "255712345678"  # Correct
phone = "+255712345678"  # Wrong
```

### Issue: "Duplicate order reference"

**Cause:** Order reference already used

**Solution:**
```python
# Use unique references
import uuid
order_ref = f"ORDER-{uuid.uuid4().hex[:12]}"

# Or catch and handle
try:
    payment = manager.create_payment(...)
except DuplicateOrderReferenceError:
    payment = manager.get_payment_by_reference(order_ref)
```

### Issue: "Insufficient balance"

**Cause:** Account balance too low for payout

**Solution:**
```python
# Check balance before payout
from clickpesa.services.account_service import AccountService

balance = AccountService().get_account_balance()
if float(balance['balance']) < payout_amount:
    # Top up account or notify admin
    pass
```

### Issue: Payment stuck in PENDING

**Cause:** Customer hasn't completed USSD prompt

**Solution:**
- Wait for customer to complete payment
- Set up periodic status checks
- Send reminder to customer
- Set timeout and cancel after certain period

### Issue: Authentication errors

**Cause:** Invalid API credentials or expired token

**Solution:**
```python
# Verify credentials in settings
# Token is automatically refreshed by library

# If issue persists, clear old tokens
from clickpesa.models import AuthToken
AuthToken.objects.all().delete()  # Force new token generation
```

---

## Security

- Store API credentials in environment variables
- Never commit credentials to version control
- Use HTTPS for all API calls (enforced by library)
- Verify webhook signatures using `CLICKPESA_CHECKSUM_SECRET`
- Restrict webhook IPs using `CLICKPESA_WEBHOOK_VERIFY_IPS`

---

## Testing

### Using Sandbox

```python
# settings.py
CLICKPESA_API_BASE_URL = 'https://sandbox.clickpesa.com'
CLICPESA_API_KEY = 'sandbox-api-key'
CLICPESA_CLIENT_ID = 'sandbox-client-id'
```

### Test Phone Numbers

ClickPesa provides test phone numbers in sandbox mode. Check their documentation for current test numbers.

---

## License

MIT License. See [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by TarXemo**
