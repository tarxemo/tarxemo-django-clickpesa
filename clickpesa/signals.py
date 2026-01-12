"""
Signals for payment events.
"""
from django.dispatch import Signal

# Signal sent when a payment transaction status changes
# Provides arguments: 
# - instance: The PaymentTransaction instance
# - created: Boolean, True if transaction was just created
# - new_status: The new status string
# - old_status: The previous status string (if updated)
payment_status_changed = Signal()

# Signal sent when a payout transaction status changes
payout_status_changed = Signal()
