"""
REST API Views for ClickPesa callbacks.
"""

import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .managers.payment_manager import PaymentManager
from .managers.payout_manager import PayoutManager
from .utils.checksum import verify_webhook_signature

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def payment_callback(request):
    """
    Handle ClickPesa payment status callbacks.
    Endpoint: /api/payments/callback/payment/
    """
    try:
        # Verify signature if configured
        if hasattr(settings, 'CLICKPESA_CHECKSUM_SECRET') and settings.CLICKPESA_CHECKSUM_SECRET:
            # Note: ClickPesa puts signature in specific header. 
            # Implement verification logic here if header format is known.
            pass

        data = json.loads(request.body)
        logger.info(f"Received payment callback: {data}")
        
        # Extract order reference
        # Payload format typically has 'orderReference' or 'reference'
        order_reference = data.get('orderReference', data.get('reference'))
        
        if not order_reference:
            logger.warning("Callback received without order reference")
            return JsonResponse({'error': 'Missing order reference'}, status=400)
            
        try:
            # Use PaymentManager to verify status and update transaction
            # This will trigger the payment_status_changed signal
            # which bhumwi_bookings.receivers listens to.
            manager = PaymentManager()
            payment = manager.check_payment_status(order_reference)
            
            return JsonResponse({
                'status': 'received',
                'order_reference': payment.order_reference,
                'payment_status': payment.status
            })
            
        except Exception as e:
            logger.error(f"Error updating payment from callback: {str(e)}")
            # Return 200 OK because we received the callback successfully, 
            # even if processing logic had an error (e.g. signal error)
            # This prevents ClickPesa from retrying endlessly if it's a logic bug.
            return JsonResponse({'status': 'processed_with_error', 'message': str(e)})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing payment callback: {str(e)}")
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

@csrf_exempt
@require_POST
def payout_callback(request):
    """
    Handle ClickPesa payout status callbacks.
    Endpoint: /api/payments/callback/payout/
    """
    try:
        data = json.loads(request.body)
        logger.info(f"Received payout callback: {data}")
        return JsonResponse({'status': 'received'})
    except Exception as e:
        logger.error(f"Error processing payout callback: {str(e)}")
        return JsonResponse({'error': 'Internal Server Error'}, status=500)
