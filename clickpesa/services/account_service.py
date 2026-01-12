"""
Account service for ClickPesa account operations.
Handles account balance and information retrieval.
"""

import logging
from typing import Dict, Any

from ..config import config
from ..constants import APIEndpoints
from ..exceptions import APIError
from ..utils.http_client import HTTPClient
from .auth_service import AuthService

logger = logging.getLogger(__name__)


class AccountService:
    """
    Service for account-related operations.
    """
    
    def __init__(self):
        self.http_client = HTTPClient(config.api_base_url)
        self.auth_service = AuthService()
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Retrieve account balance.
        
        Returns:
            Dictionary containing:
                - currency: Account currency
                - balance: Current balance
                
        Raises:
            APIError: If balance retrieval fails
        """
        logger.info("Retrieving account balance")
        
        try:
            # Get auth headers
            headers = self.auth_service.get_auth_header()
            
            # Make API request
            response = self.http_client.get(
                endpoint=APIEndpoints.ACCOUNT_BALANCE,
                headers=headers
            )
            
            balance = response.get('balance', 0)
            currency = response.get('currency', 'TZS')
            
            logger.info(f"Account balance retrieved: {currency} {balance}")
            return response
        
        except Exception as e:
            logger.error(f"Failed to retrieve account balance: {str(e)}")
            raise APIError(f"Failed to get account balance: {str(e)}")
