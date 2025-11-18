"""Custom exceptions for Keycloak MCP server.

This module defines specific exception types to help students understand
error handling and create more maintainable code.
"""


class KeycloakError(Exception):
    """Base exception for all Keycloak-related errors.

    This follows the pattern of creating a base exception class that all
    other domain-specific exceptions inherit from. This makes it easy to
    catch all Keycloak errors with a single except clause if needed.
    """
    pass


class KeycloakAuthError(KeycloakError):
    """Raised when authentication with Keycloak fails.

    Examples:
        - Invalid client credentials
        - Token endpoint unreachable
        - Malformed token response
    """
    pass


class KeycloakAPIError(KeycloakError):
    """Raised when a Keycloak API request fails.

    Examples:
        - 404 Not Found (realm doesn't exist)
        - 403 Forbidden (insufficient permissions)
        - 500 Internal Server Error
    """

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize the API error with an optional HTTP status code.

        Args:
            message: Human-readable error description
            status_code: HTTP status code from the failed request
        """
        super().__init__(message)
        self.status_code = status_code


class KeycloakConfigError(KeycloakError):
    """Raised when there's a configuration error.

    Examples:
        - Missing environment variables
        - Invalid URL format
        - Empty required parameters
    """
    pass
