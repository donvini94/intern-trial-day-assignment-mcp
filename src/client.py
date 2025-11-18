"""Keycloak API client for MCP server.

This module provides a clean abstraction over the Keycloak Admin REST API.
It demonstrates best practices for building API clients in Python:
- Type hints for better IDE support and type checking
- Custom exceptions for specific error cases
- Token management with automatic refresh
- Input validation
- Comprehensive documentation
"""

import logging
import time
from typing import Any

import requests

from exceptions import KeycloakAPIError, KeycloakAuthError, KeycloakConfigError
from keycloak_models import RealmRepresentation, TokenResponse, UserRepresentation

logger = logging.getLogger(__name__)


class KeycloakClient:
    """Client for interacting with the Keycloak Admin REST API.

    This client handles authentication, token management, and provides
    methods to interact with Keycloak resources like realms and users.

    The client uses the OAuth2 client credentials flow to authenticate,
    which is appropriate for service-to-service communication.

    Attributes:
        base_url: The base URL of the Keycloak server
        client_id: The OAuth2 client ID
        client_secret: The OAuth2 client secret
        realm: The realm to authenticate against (default: "master")
        access_token: The current access token (None if not authenticated)
        token_expiry: Unix timestamp when the current token expires

    Example:
        >>> client = KeycloakClient(
        ...     base_url="http://localhost:8080",
        ...     client_id="admin-cli",
        ...     client_secret="secret"
        ... )
        >>> realms = client.get_realms()
        >>> print(f"Found {len(realms)} realms")
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        realm: str = "master",
    ):
        """Initialize the Keycloak client.

        Args:
            base_url: The base URL of the Keycloak server (e.g., "http://localhost:8080")
            client_id: The OAuth2 client ID for authentication
            client_secret: The OAuth2 client secret for authentication
            realm: The realm to authenticate against (default: "master")

        Raises:
            KeycloakConfigError: If any required parameter is empty or invalid
        """
        # Validate inputs
        if not base_url:
            raise KeycloakConfigError("base_url cannot be empty")
        if not client_id:
            raise KeycloakConfigError("client_id cannot be empty")
        if not client_secret:
            raise KeycloakConfigError("client_secret cannot be empty")
        if not realm:
            raise KeycloakConfigError("realm cannot be empty")

        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.realm = realm
        self.access_token: str | None = None
        self.token_expiry: float = 0

    def _get_access_token(self) -> str:
        """Obtain a new access token from Keycloak.

        This method implements the OAuth2 client credentials flow.
        The token endpoint is part of the OpenID Connect standard:
        /.well-known/openid-configuration

        Returns:
            The access token string

        Raises:
            KeycloakAuthError: If authentication fails for any reason

        Note:
            This method also updates self.token_expiry based on the
            expires_in value from the token response.
        """
        token_endpoint = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        client_credentials = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(token_endpoint, data=client_credentials, timeout=10)
            response.raise_for_status()

            # Parse the response into a Pydantic model
            token_data = TokenResponse.model_validate(response.json())

            # Track token expiration (subtract 10 seconds for safety margin)
            self.token_expiry = time.time() + token_data.expires_in - 10

            return token_data.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise KeycloakAuthError(f"Authentication failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse token response: {e}")
            raise KeycloakAuthError(f"Invalid token response format: {e}") from e

    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token.

        This method checks if we have a token and if it's still valid.
        If not, it obtains a new one. This is called before each API request.
        """
        if not self.access_token or time.time() >= self.token_expiry:
            logger.debug("Token missing or expired, obtaining new token")
            self.access_token = self._get_access_token()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request to the Keycloak API.

        This is the core method that handles all HTTP communication with
        Keycloak. It manages authentication, retries on token expiration,
        and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (e.g., "/admin/realms")
            **kwargs: Additional arguments to pass to requests.request()

        Returns:
            The JSON response from the API, or None for 204 No Content

        Raises:
            KeycloakAPIError: If the API request fails

        Note:
            This method automatically retries once with a fresh token if
            it receives a 401 Unauthorized response.
        """
        self._ensure_valid_token()

        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        # Set default timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = 10

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()

            # 204 No Content - successful request with no body
            if response.status_code == 204:
                return None

            return response.json()

        except requests.exceptions.HTTPError as e:
            # Handle 401 Unauthorized - token might have expired
            if e.response.status_code == 401:
                logger.info("Received 401, refreshing token and retrying")
                self.access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"

                # Retry once with new token
                try:
                    response = requests.request(method, url, headers=headers, **kwargs)
                    response.raise_for_status()
                    return response.json() if response.status_code != 204 else None
                except requests.exceptions.RequestException as retry_error:
                    logger.error(f"Retry after token refresh failed: {retry_error}")
                    raise KeycloakAPIError(
                        f"Request failed after token refresh: {retry_error}",
                        status_code=getattr(retry_error.response, "status_code", None),
                    ) from retry_error
            else:
                logger.error(f"Keycloak API error: {e}")
                raise KeycloakAPIError(
                    f"API request failed: {e}",
                    status_code=e.response.status_code,
                ) from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise KeycloakAPIError(f"Failed to communicate with Keycloak: {e}") from e

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def get_realms(self) -> list[RealmRepresentation]:
        """Get a list of all realms in the Keycloak server.

        Returns:
            A list of realm representations (Pydantic models).
            Each realm contains information like id, name, enabled status, etc.

            Example return value:
            [
                RealmRepresentation(
                    id="master",
                    realm="master",
                    displayName="Keycloak",
                    enabled=True,
                    ...
                ),
                RealmRepresentation(
                    id="myrealm",
                    realm="myrealm",
                    enabled=True,
                    ...
                )
            ]

        Raises:
            KeycloakAPIError: If the request fails
        """
        response_data = self._make_request("GET", "/admin/realms")
        return [RealmRepresentation.model_validate(realm) for realm in response_data]

    def get_users(self, realm: str, max_users: int = 100) -> list[UserRepresentation]:
        """Get a list of users from a specific realm.

        Args:
            realm: The name of the realm to get users from
            max_users: Maximum number of users to return (default: 100)

        Returns:
            A list of user representations (Pydantic models).
            Each user contains information like id, username, email, etc.

            Example return value:
            [
                UserRepresentation(
                    id="8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
                    username="john.doe",
                    email="john.doe@example.com",
                    firstName="John",
                    lastName="Doe",
                    enabled=True,
                    ...
                )
            ]

        Raises:
            KeycloakAPIError: If the request fails (e.g., realm doesn't exist)
        """
        # Validate input
        if not realm:
            raise KeycloakConfigError("realm parameter cannot be empty")

        endpoint = f"/admin/realms/{realm}/users"
        # Use query parameters to limit results
        params = {"max": max_users}
        response_data = self._make_request("GET", endpoint, params=params)
        return [UserRepresentation.model_validate(user) for user in response_data]

    def get_user_info(self, realm: str, user_id: str) -> UserRepresentation:
        """Get detailed information about a specific user.

        Args:
            realm: The name of the realm the user belongs to
            user_id: The unique ID of the user (not the username!)

        Returns:
            A user representation (Pydantic model) containing detailed user information

            Example return value:
            UserRepresentation(
                id="8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
                username="john.doe",
                email="john.doe@example.com",
                firstName="John",
                lastName="Doe",
                enabled=True,
                emailVerified=False,
                createdTimestamp=1609459200000,
                ...
            )

        Raises:
            KeycloakAPIError: If the request fails (e.g., user or realm doesn't exist)
        """
        # Validate inputs
        if not realm:
            raise KeycloakConfigError("realm parameter cannot be empty")
        if not user_id:
            raise KeycloakConfigError("user_id parameter cannot be empty")

        endpoint = f"/admin/realms/{realm}/users/{user_id}"
        response_data = self._make_request("GET", endpoint)
        return UserRepresentation.model_validate(response_data)
