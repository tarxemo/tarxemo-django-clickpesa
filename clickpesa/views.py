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
from .utils.checksum import verify_webhook_signature, verify_webhook_ip

logger = logging.getLogger(__name__)

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@csrf_exempt
@require_POST
def payment_callback(request):
    """
    Handle ClickPesa payment status callbacks.
    """
    # 1. IP Verification
    allowed_ips = getattr(settings, 'CLICKPESA_WEBHOOK_VERIFY_IPS', [])
    if allowed_ips and not verify_webhook_ip(_get_client_ip(request), allowed_ips):
        logger.warning(f"Unauthorized Webhook IP: {_get_client_ip(request)}")
        return HttpResponse(status=403)

    try:
        data = json.loads(request.body)
        logger.info(f"Received payment callback: {data}")
        
        # 2. Signature Verification (if secret configured)
        secret = getattr(settings, 'CLICKPESA_CHECKSUM_SECRET', None)
        signature = request.headers.get('X-ClickPesa-Signature')
        if secret and signature and not verify_webhook_signature(data, signature, secret):
            logger.warning("Invalid Webhook Signature")
            return HttpResponse(status=401)

        order_reference = data.get('orderReference', data.get('reference'))
        if not order_reference:
            return JsonResponse({'error': 'Missing reference'}, status=400)
            
        manager = PaymentManager()
        manager.check_payment_status(order_reference)
        return JsonResponse({'status': 'received'})
        
    except Exception as e:
        logger.error(f"Error processing payment callback: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
@require_POST
def payout_callback(request):
    """
    Handle ClickPesa payout status callbacks.
    """
    allowed_ips = getattr(settings, 'CLICKPESA_WEBHOOK_VERIFY_IPS', [])
    if allowed_ips and not verify_webhook_ip(_get_client_ip(request), allowed_ips):
        return HttpResponse(status=403)

    try:
        data = json.loads(request.body)
        logger.info(f"Received payout callback: {data}")
        
        order_reference = data.get('orderReference', data.get('reference'))
        if not order_reference:
            return JsonResponse({'error': 'Missing reference'}, status=400)

        manager = PayoutManager()
        manager.check_payout_status(order_reference)
        return JsonResponse({'status': 'received'})
    except Exception as e:
        logger.error(f"Error processing payout callback: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})
