"""Type definitions for Keycloak API responses.

This module demonstrates how to use Pydantic models to create structured types
for API responses. This provides better validation, IDE autocomplete, and type checking
while documenting the expected structure of API responses.
"""

from pydantic import BaseModel, ConfigDict


class RealmRepresentation(BaseModel):
    """Represents a Keycloak realm.

    Example JSON from Keycloak API:
    {
        "id": "master",
        "realm": "master",
        "displayName": "Keycloak",
        "enabled": true,
        "sslRequired": "external",
        "registrationAllowed": false,
        "loginWithEmailAllowed": true,
        ...
    }
    """

    model_config = ConfigDict(
        # Allow extra fields from API that we don't explicitly define
        extra="allow",
        # Use field names as-is from API (e.g., "displayName")
        populate_by_name=True,
    )

    id: str
    realm: str
    display_name: str | None = None
    enabled: bool | None = None
    ssl_required: str | None = None
    registration_allowed: bool | None = None
    login_with_email_allowed: bool | None = None
    # Note: Keycloak returns many more fields, but these are the most common


class UserRepresentation(BaseModel):
    """Represents a Keycloak user.

    Example JSON from Keycloak API:
    {
        "id": "8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
        "username": "john.doe",
        "enabled": true,
        "emailVerified": false,
        "firstName": "John",
        "lastName": "Doe",
        "email": "john.doe@example.com",
        "createdTimestamp": 1609459200000,
        ...
    }
    """

    model_config = ConfigDict(
        # Allow extra fields from API that we don't explicitly define
        extra="allow",
        # Use field names as-is from API (e.g., "emailVerified", "firstName")
        populate_by_name=True,
    )

    id: str
    username: str
    enabled: bool
    email_verified: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    created_timestamp: int | None = None
    # Note: Many more fields available in the actual API response


class TokenResponse(BaseModel):
    """Represents an OAuth2 token response.

    This is the response from the token endpoint. All fields are required
    for a successful token response.

    Example JSON:
    {
        "access_token": "eyJhbGciOiJSUzI1NiIs...",
        "expires_in": 300,
        "refresh_expires_in": 1800,
        "token_type": "Bearer",
        "not-before-policy": 0,
        "scope": "profile email"
    }
    """

    model_config = ConfigDict(
        # Allow extra fields from API that we don't explicitly define
        extra="allow",
        # Use field names as-is from API (e.g., "access_token")
        populate_by_name=True,
    )

    access_token: str
    expires_in: int
    refresh_expires_in: int
    token_type: str
    scope: str
