# tarxemo-django-clickpesa

A clean, service-oriented Django implementation for integrating ClickPesa payment and payout services.

## Features

- ✅ **Mobile Money Payments**: Initiate USSD push payments.
- ✅ **Payouts**: Manage B2C and B2B payouts via mobile money or bank transfer.
- ✅ **Status Tracking**: Orchestrate transaction lifecycles with local database records.
- ✅ **Django Signals**: Decoupled event system to notify your app of status changes (Success, Failed, etc.).
- ✅ **Automatic Authentication**: Token management and caching built-in.
- ✅ **Webhooks Support**: Ready-to-use callback views with checksum verification.

## Installation

```bash
pip install tarxemo-django-clickpesa
```

## Configuration

Add `clickpesa` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'clickpesa',
]
```

Configure your ClickPesa credentials in `settings.py`:

```python
CLICKPESA_API_BASE_URL = 'https://api.clickpesa.com' # Use sandbox for testing
CLICKPESA_API_KEY = 'your-api-key'
CLICKPESA_CLIENT_ID = 'your-client-id'
CLICKPESA_CHECKSUM_SECRET = 'your-webhook-secret'
```

## Usage

### Initiate a Payment

```python
from clickpesa.managers.payment_manager import PaymentManager

manager = PaymentManager()
payment = manager.create_payment(
    amount=1000.0,
    phone_number="255712345678",
    order_reference="ORDER-123",
    currency="TZS"
)
```

### Listening for Status Changes

```python
from django.dispatch import receiver
from clickpesa.signals import payment_status_changed

@receiver(payment_status_changed)
def handle_payment_update(sender, instance, new_status, **kwargs):
    if new_status == 'SUCCESS':
        # Ship items, enroll user, etc.
        pass
```

## License

MIT
