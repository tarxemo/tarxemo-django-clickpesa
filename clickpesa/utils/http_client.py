"""
HTTP client for ClickPesa API communication.
"""

import requests
import logging
from typing import Dict, Any, Optional
from clickpesa.exceptions import APIError, AuthenticationError
from clickpesa.constants import DEFAULT_TIMEOUT, MAX_RETRIES

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    HTTP client wrapper for ClickPesa API requests.
    Handles request/response, error handling, retries, and logging.
    """
    
    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def _get_full_url(self, endpoint: str) -> str:
        """Get full URL for endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _log_request(self, method: str, url: str, headers: Dict, data: Optional[Dict] = None):
        """Log API request details."""
        logger.info(f"ClickPesa API Request: {method} {url}")
        logger.debug(f"Headers: {self._sanitize_headers(headers)}")
        if data:
            logger.debug(f"Payload: {data}")
    
    def _log_response(self, response: requests.Response):
        """Log API response details."""
        logger.info(f"ClickPesa API Response: {response.status_code}")
        try:
            logger.debug(f"Response: {response.json()}")
        except:
            logger.debug(f"Response: {response.text}")
    
    def _sanitize_headers(self, headers: Dict) -> Dict:
        """Remove sensitive data from headers for logging."""
        sanitized = headers.copy()
        if 'Authorization' in sanitized:
            sanitized['Authorization'] = 'Bearer ***'
        if 'api-key' in sanitized:
            sanitized['api-key'] = '***'
        return sanitized
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and extract data.
        
        Args:
            response: Response object from requests
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If response indicates an error
            AuthenticationError: If authentication fails
        """
        self._log_response(response)
        
        # Check for HTTP errors
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed. Please check your API credentials.",
                error_code=401,
                response_data=response.text
            )
        
        if response.status_code == 403:
            raise AuthenticationError(
                "Access forbidden. Please check your API permissions.",
                error_code=403,
                response_data=response.text
            )
        
        if response.status_code >= 400:
            error_message = f"API request failed with status {response.status_code}"
            try:
                error_data = response.json()
                error_message = error_data.get('message', error_message)
            except:
                error_message = response.text or error_message
            
            raise APIError(
                error_message,
                error_code=response.status_code,
                response_data=response.text
            )
        
        # Parse JSON response
        try:
            return response.json()
        except ValueError as e:
            raise APIError(
                f"Failed to parse API response: {str(e)}",
                response_data=response.text
            )
    
    def post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Make POST request to API.
        
        Args:
            endpoint: API endpoint path
            data: Request payload
            headers: Request headers
            retries: Number of retries on failure
            
        Returns:
            Response data
        """
        url = self._get_full_url(endpoint)
        headers = headers or {}
        headers.setdefault('Content-Type', 'application/json')
        
        self._log_request('POST', url, headers, data)
        
        for attempt in range(retries):
            try:
                response = self.session.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                return self._handle_response(response)
            
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == retries - 1:
                    raise APIError(f"Connection failed after {retries} attempts: {str(e)}")
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {str(e)}")
                continue
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Make GET request to API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Request headers
            retries: Number of retries on failure
            
        Returns:
            Response data
        """
        url = self._get_full_url(endpoint)
        headers = headers or {}
        
        self._log_request('GET', url, headers)
        
        for attempt in range(retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
                return self._handle_response(response)
            
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == retries - 1:
                    raise APIError(f"Connection failed after {retries} attempts: {str(e)}")
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {str(e)}")
                continue
    
    def close(self):
        """Close the session."""
        self.session.close()
