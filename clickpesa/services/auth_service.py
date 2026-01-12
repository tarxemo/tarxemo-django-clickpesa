"""
Authentication service for ClickPesa API.
Handles token generation and caching.
"""

import logging
from typing import Optional
from django.utils import timezone
from datetime import timedelta

from ..config import config
from ..constants import APIEndpoints, TOKEN_REFRESH_BUFFER_MINUTES
from ..exceptions import AuthenticationError
from ..models import AuthToken
from ..utils.http_client import HTTPClient

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for managing ClickPesa authentication tokens.
    Implements token caching to minimize API calls.
    """
    
    def __init__(self):
        self.http_client = HTTPClient(config.api_base_url)
    
    def generate_token(self) -> str:
        """
        Generate a new JWT token from ClickPesa API.
        
        Returns:
            JWT token string (with Bearer prefix)
            
        Raises:
            AuthenticationError: If token generation fails
        """
        logger.info("Generating new ClickPesa authentication token")
        
        try:
            # Prepare headers
            headers = {
                'client-id': config.client_id,
                'api-key': config.api_key,
            }
            
            # Make API request
            response = self.http_client.post(
                endpoint=APIEndpoints.GENERATE_TOKEN,
                headers=headers
            )
            
            # Validate response
            if not response.get('success'):
                raise AuthenticationError(
                    "Token generation failed: API returned success=false",
                    response_data=response
                )
            
            token = response.get('token')
            if not token:
                raise AuthenticationError(
                    "Token generation failed: No token in response",
                    response_data=response
                )
            
            # Cache token in database
            AuthToken.create_token(token)
            
            logger.info("Successfully generated and cached new token")
            return token
        
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate token: {str(e)}")
            raise AuthenticationError(f"Token generation failed: {str(e)}")
    
    def get_valid_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid authentication token.
        Returns cached token if available and valid, otherwise generates new one.
        
        Args:
            force_refresh: Force generation of new token even if cached token exists
            
        Returns:
            Valid JWT token string (with Bearer prefix)
        """
        if force_refresh:
            logger.info("Force refresh requested, generating new token")
            return self.generate_token()
        
        # Try to get cached token
        cached_token = AuthToken.get_valid_token()
        
        if cached_token:
            # Check if token is close to expiry (refresh buffer)
            refresh_threshold = timezone.now() + timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
            
            if cached_token.expires_at > refresh_threshold:
                logger.debug("Using cached token")
                return cached_token.token
            else:
                logger.info("Cached token close to expiry, refreshing")
        else:
            logger.info("No valid cached token found")
        
        # Generate new token
        return self.generate_token()
    
    def invalidate_token(self):
        """
        Invalidate all cached tokens.
        Useful when you know a token is invalid.
        """
        logger.info("Invalidating all cached tokens")
        AuthToken.objects.filter(is_active=True).update(is_active=False)
    
    def get_auth_header(self, force_refresh: bool = False) -> dict:
        """
        Get authorization header for API requests.
        
        Args:
            force_refresh: Force generation of new token
            
        Returns:
            Dictionary with Authorization header
        """
        token = self.get_valid_token(force_refresh=force_refresh)
        return {'Authorization': token}
