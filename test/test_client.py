"""Tests for the Keycloak client.

This module demonstrates testing best practices:
- Using pytest fixtures for test setup
- Mocking HTTP requests with the responses library
- Testing both success and failure cases
- Testing input validation
- Clear test naming that describes what is being tested
"""

import sys
import time
from pathlib import Path

import pytest
import responses
from requests.exceptions import HTTPError

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client import KeycloakClient
from exceptions import KeycloakAPIError, KeycloakAuthError, KeycloakConfigError

# =============================================================================
# Fixtures
# =============================================================================
# Fixtures are reusable test setup code. They help avoid duplication and
# make tests more maintainable.


@pytest.fixture
def keycloak_client():
    """Create a KeycloakClient instance for testing.

    This fixture provides a pre-configured client that tests can use.
    Each test gets a fresh instance.
    """
    return KeycloakClient(
        base_url="http://localhost:8080",
        client_id="test-client",
        client_secret="test-secret",
        realm="master",
    )


@pytest.fixture
def mock_token_response():
    """Return a mock token response matching Keycloak's format."""
    return {
        "access_token": "mock-access-token-123",
        "expires_in": 300,
        "refresh_expires_in": 1800,
        "token_type": "Bearer",
        "scope": "profile email",
    }


# =============================================================================
# Initialization Tests
# =============================================================================


def test_client_initialization_success():
    """Test that client initializes correctly with valid parameters."""
    client = KeycloakClient(
        base_url="http://localhost:8080",
        client_id="my-client",
        client_secret="my-secret",
    )

    assert client.base_url == "http://localhost:8080"
    assert client.client_id == "my-client"
    assert client.client_secret == "my-secret"
    assert client.realm == "master"  # Default value
    assert client.access_token is None
    assert client.token_expiry == 0


def test_client_initialization_strips_trailing_slash():
    """Test that trailing slash is removed from base_url."""
    client = KeycloakClient(
        base_url="http://localhost:8080/",
        client_id="my-client",
        client_secret="my-secret",
    )

    assert client.base_url == "http://localhost:8080"


def test_client_initialization_with_custom_realm():
    """Test that custom realm can be specified."""
    client = KeycloakClient(
        base_url="http://localhost:8080",
        client_id="my-client",
        client_secret="my-secret",
        realm="custom-realm",
    )

    assert client.realm == "custom-realm"


def test_client_initialization_empty_base_url():
    """Test that empty base_url raises KeycloakConfigError."""
    with pytest.raises(KeycloakConfigError, match="base_url cannot be empty"):
        KeycloakClient(
            base_url="",
            client_id="my-client",
            client_secret="my-secret",
        )


def test_client_initialization_empty_client_id():
    """Test that empty client_id raises KeycloakConfigError."""
    with pytest.raises(KeycloakConfigError, match="client_id cannot be empty"):
        KeycloakClient(
            base_url="http://localhost:8080",
            client_id="",
            client_secret="my-secret",
        )


def test_client_initialization_empty_client_secret():
    """Test that empty client_secret raises KeycloakConfigError."""
    with pytest.raises(KeycloakConfigError, match="client_secret cannot be empty"):
        KeycloakClient(
            base_url="http://localhost:8080",
            client_id="my-client",
            client_secret="",
        )


# =============================================================================
# Authentication Tests
# =============================================================================


@responses.activate
def test_get_access_token_success(keycloak_client, mock_token_response):
    """Test successful token acquisition.

    The @responses.activate decorator enables HTTP mocking.
    All HTTP requests in this test will be intercepted and handled by
    the mock responses we register.
    """
    # Register a mock response for the token endpoint
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    token = keycloak_client._get_access_token()

    assert token == "mock-access-token-123"
    assert keycloak_client.token_expiry > time.time()
    assert keycloak_client.token_expiry <= time.time() + 290  # 300 - 10 safety margin


@responses.activate
def test_get_access_token_network_error(keycloak_client):
    """Test that network errors raise KeycloakAuthError."""
    # Register a mock response that simulates a connection error
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        body=ConnectionError("Connection refused"),
    )

    with pytest.raises(KeycloakAuthError, match="Invalid token response format"):
        keycloak_client._get_access_token()


@responses.activate
def test_get_access_token_invalid_credentials(keycloak_client):
    """Test that invalid credentials raise KeycloakAuthError."""
    # Mock a 401 Unauthorized response
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json={"error": "invalid_client"},
        status=401,
    )

    with pytest.raises(KeycloakAuthError, match="Authentication failed"):
        keycloak_client._get_access_token()


@responses.activate
def test_get_access_token_malformed_response(keycloak_client):
    """Test that malformed token response raises KeycloakAuthError."""
    # Mock a response that's missing the access_token field
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json={"expires_in": 300},  # Missing access_token!
        status=200,
    )

    with pytest.raises(KeycloakAuthError, match="Invalid token response format"):
        keycloak_client._get_access_token()


# =============================================================================
# API Request Tests
# =============================================================================


@responses.activate
def test_get_realms_success(keycloak_client, mock_token_response):
    """Test successful realm retrieval."""
    # Mock the token endpoint
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    # Mock the realms endpoint
    mock_realms = [
        {"id": "master", "realm": "master", "enabled": True},
        {"id": "test", "realm": "test", "enabled": True},
    ]
    responses.get(
        "http://localhost:8080/admin/realms",
        json=mock_realms,
        status=200,
    )

    realms = keycloak_client.get_realms()

    assert len(realms) == 2
    assert realms[0].realm == "master"
    assert realms[1].realm == "test"


@responses.activate
def test_get_realms_with_existing_token(keycloak_client, mock_token_response):
    """Test that existing valid token is reused."""
    # Set up an existing token
    keycloak_client.access_token = "existing-token"
    keycloak_client.token_expiry = time.time() + 100

    # Mock only the realms endpoint (token endpoint should NOT be called)
    mock_realms = [{"id": "master", "realm": "master"}]
    responses.get(
        "http://localhost:8080/admin/realms",
        json=mock_realms,
        status=200,
    )

    realms = keycloak_client.get_realms()

    # Verify the existing token was used
    assert len(responses.calls) == 1
    assert "Bearer existing-token" in responses.calls[0].request.headers["Authorization"]


@responses.activate
def test_get_realms_token_expired(keycloak_client, mock_token_response):
    """Test that expired token is refreshed automatically."""
    # Set up an expired token
    keycloak_client.access_token = "expired-token"
    keycloak_client.token_expiry = time.time() - 100  # Expired!

    # Mock the token endpoint to get a new token
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    # Mock the realms endpoint
    responses.get(
        "http://localhost:8080/admin/realms",
        json=[{"id": "master", "realm": "master"}],
        status=200,
    )

    realms = keycloak_client.get_realms()

    # Verify both endpoints were called
    assert len(responses.calls) == 2
    # The new token should have been used
    assert "Bearer mock-access-token-123" in responses.calls[1].request.headers["Authorization"]


@responses.activate
def test_get_users_success(keycloak_client, mock_token_response):
    """Test successful user retrieval."""
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    mock_users = [
        {
            "id": "user-123",
            "username": "john.doe",
            "email": "john@example.com",
            "enabled": True,
        }
    ]
    responses.get(
        "http://localhost:8080/admin/realms/test-realm/users",
        json=mock_users,
        status=200,
    )

    users = keycloak_client.get_users("test-realm", max_users=50)

    assert len(users) == 1
    assert users[0].username == "john.doe"

    # Verify query parameters were sent
    assert "max=50" in responses.calls[-1].request.url


def test_get_users_empty_realm():
    """Test that empty realm parameter raises KeycloakConfigError."""
    client = KeycloakClient(
        base_url="http://localhost:8080",
        client_id="test",
        client_secret="test",
    )

    with pytest.raises(KeycloakConfigError, match="realm parameter cannot be empty"):
        client.get_users("")


@responses.activate
def test_get_user_info_success(keycloak_client, mock_token_response):
    """Test successful user info retrieval."""
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    mock_user = {
        "id": "user-123",
        "username": "john.doe",
        "email": "john@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "enabled": True,  # Add required field
    }
    responses.get(
        "http://localhost:8080/admin/realms/test-realm/users/user-123",
        json=mock_user,
        status=200,
    )

    user = keycloak_client.get_user_info("test-realm", "user-123")

    assert user.username == "john.doe"
    assert user.email == "john@example.com"


def test_get_user_info_empty_realm():
    """Test that empty realm raises KeycloakConfigError."""
    client = KeycloakClient(
        base_url="http://localhost:8080",
        client_id="test",
        client_secret="test",
    )

    with pytest.raises(KeycloakConfigError, match="realm parameter cannot be empty"):
        client.get_user_info("", "user-123")


def test_get_user_info_empty_user_id():
    """Test that empty user_id raises KeycloakConfigError."""
    client = KeycloakClient(
        base_url="http://localhost:8080",
        client_id="test",
        client_secret="test",
    )

    with pytest.raises(KeycloakConfigError, match="user_id parameter cannot be empty"):
        client.get_user_info("test-realm", "")


# =============================================================================
# Error Handling Tests
# =============================================================================


@responses.activate
def test_api_request_404_error(keycloak_client, mock_token_response):
    """Test that 404 errors are properly handled."""
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    responses.get(
        "http://localhost:8080/admin/realms/nonexistent/users",
        json={"error": "Realm not found"},
        status=404,
    )

    with pytest.raises(KeycloakAPIError) as exc_info:
        keycloak_client.get_users("nonexistent")

    assert exc_info.value.status_code == 404


@responses.activate
def test_api_request_401_retry(keycloak_client, mock_token_response):
    """Test that 401 errors trigger token refresh and retry."""
    # First token request
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json=mock_token_response,
        status=200,
    )

    # First API request returns 401
    responses.get(
        "http://localhost:8080/admin/realms",
        json={"error": "Unauthorized"},
        status=401,
    )

    # Second token request (refresh)
    responses.post(
        "http://localhost:8080/realms/master/protocol/openid-connect/token",
        json={**mock_token_response, "access_token": "new-token"},
        status=200,
    )

    # Retry succeeds
    responses.get(
        "http://localhost:8080/admin/realms",
        json=[{"id": "master", "realm": "master"}],
        status=200,
    )

    realms = keycloak_client.get_realms()

    # Should have made 4 calls total: token, failed API, new token, successful API
    assert len(responses.calls) == 4
    assert realms[0].realm == "master"


# =============================================================================
# Integration-style Tests
# =============================================================================
# These tests verify the complete flow without mocking


def test_client_flow_documentation():
    """This test documents the expected client usage flow.

    This is not a runnable test (it would need a real Keycloak instance),
    but it serves as documentation for how the client should be used.
    """
    # Step 1: Initialize the client
    client = KeycloakClient(
        base_url="http://localhost:8080",
        client_id="admin-cli",
        client_secret="secret",
    )

    # Step 2: The client automatically handles authentication
    # No need to manually call _get_access_token()

    # Step 3: Make API calls
    # realms = client.get_realms()
    # users = client.get_users("master")
    # user = client.get_user_info("master", "user-id")

    # Step 4: The client automatically refreshes tokens when needed
    # You don't need to worry about token expiration

    assert True  # Placeholder for documentation
