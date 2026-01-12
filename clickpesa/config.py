"""
Configuration management for ClickPesa payment utility.
"""

from django.conf import settings
from .exceptions import ConfigurationError


class ClickPesaConfig:
    """
    Configuration manager for ClickPesa API settings.
    Loads and validates settings from Django settings.
    """
    
    def __init__(self):
        self._validate_settings()
    
    @property
    def api_base_url(self):
        """Get ClickPesa API base URL."""
        return getattr(
            settings, 
            'CLICKPESA_API_BASE_URL', 
            'https://api.clickpesa.com'
        )
    
    @property
    def api_key(self):
        """Get ClickPesa API key."""
        api_key = getattr(settings, 'CLICPESA_API_KEY', '')
        if not api_key:
            raise ConfigurationError(
                "CLICPESA_API_KEY is not configured in Django settings. "
                "Please add it to your settings.py or .env file."
            )
        return api_key
    
    @property
    def client_id(self):
        """Get ClickPesa client ID."""
        client_id = getattr(settings, 'CLICPESA_CLIENT_ID', '')
        if not client_id:
            raise ConfigurationError(
                "CLICPESA_CLIENT_ID is not configured in Django settings. "
                "Please add it to your settings.py or .env file."
            )
        return client_id
    
    @property
    def checksum_secret(self):
        """Get checksum secret (optional)."""
        return getattr(settings, 'CLICKPESA_CHECKSUM_SECRET', '')
    
    @property
    def default_currency(self):
        """Get default currency."""
        return getattr(settings, 'DEFAULT_CURRENCY', 'TZS')
    
    @property
    def success_url(self):
        """Get payment success callback URL."""
        return getattr(settings, 'CLICKPESA_SUCCESS_URL', '')
    
    @property
    def cancel_url(self):
        """Get payment cancel callback URL."""
        return getattr(settings, 'CLICKPESA_CANCEL_URL', '')
    
    @property
    def webhook_verify_ips(self):
        """Get list of IPs to verify webhooks from."""
        return getattr(settings, 'CLICKPESA_WEBHOOK_VERIFY_IPS', [])
    
    @property
    def enable_checksum(self):
        """Check if checksum is enabled."""
        return bool(self.checksum_secret)
    
    def _validate_settings(self):
        """
        Validate that required settings are present.
        Raises ConfigurationError if validation fails.
        """
        # Check that API base URL is set
        if not self.api_base_url:
            raise ConfigurationError("CLICKPESA_API_BASE_URL is not configured.")
        
        # API key and client ID validation happens in their property getters
        # This allows the config object to be created, but will fail when
        # trying to use the API
    
    def get_full_url(self, endpoint):
        """
        Get full URL for an API endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL combining base URL and endpoint
        """
        base = self.api_base_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        return f"{base}/{endpoint}"


# Singleton instance
config = ClickPesaConfig()
