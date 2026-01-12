"""
Checksum generation and webhook signature verification utilities.
"""

import hashlib
import hmac
import json
from typing import Dict, Any


def generate_checksum(payload: Dict[str, Any], secret: str) -> str:
    """
    Generate checksum for request payload.
    
    ClickPesa checksum is typically an HMAC-SHA256 hash of the payload.
    Check ClickPesa documentation for exact implementation.
    
    Args:
        payload: Request payload dictionary
        secret: Checksum secret key
        
    Returns:
        Checksum string
    """
    if not secret:
        return ""
    
    # Sort payload keys for consistent hashing
    sorted_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    # Generate HMAC-SHA256 hash
    checksum = hmac.new(
        secret.encode('utf-8'),
        sorted_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return checksum


def verify_webhook_signature(
    payload: Dict[str, Any],
    signature: str,
    secret: str
) -> bool:
    """
    Verify webhook signature from ClickPesa.
    
    Args:
        payload: Webhook payload
        signature: Signature from webhook headers
        secret: Webhook secret key
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature:
        return False
    
    # Generate expected signature
    expected_signature = generate_checksum(payload, secret)
    
    # Compare signatures using constant-time comparison
    return hmac.compare_digest(expected_signature, signature)


def verify_webhook_ip(request_ip: str, allowed_ips: list) -> bool:
    """
    Verify that webhook request comes from allowed IP addresses.
    
    Args:
        request_ip: IP address of the request
        allowed_ips: List of allowed IP addresses
        
    Returns:
        True if IP is allowed, False otherwise
    """
    if not allowed_ips:
        # If no IPs configured, allow all (not recommended for production)
        return True
    
    return request_ip in allowed_ips
