"""Keycloak MCP Server.

This module implements an MCP (Model Context Protocol) server that exposes
Keycloak admin functionality as tools that can be called by AI models.

The server provides tools for:
- Listing realms
- Listing users in a realm
- Getting detailed user information

For students: This demonstrates how to build an MCP server that wraps
an existing API, making it accessible to AI assistants.
"""

import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from client import KeycloakClient
from exceptions import KeycloakConfigError

# Configure logging once at module level
# Note: In a larger application, you'd configure this in main() instead
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
# The name "keycloak-werki" identifies this server to MCP clients
mcp = FastMCP("keycloak-werki")

# Load environment variables from .env file
load_dotenv()


def validate_environment() -> tuple[str, str, str]:
    """Validate that all required environment variables are set.

    This function demonstrates defensive programming - we check configuration
    at startup rather than discovering problems during operation.

    Returns:
        Tuple of (keycloak_url, client_id, client_secret)

    Raises:
        KeycloakConfigError: If any required environment variable is missing or empty
    """
    keycloak_url = os.getenv("KEYCLOAK_URL", "").strip()
    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()

    missing = []
    if not keycloak_url:
        missing.append("KEYCLOAK_URL")
    if not client_id:
        missing.append("CLIENT_ID")
    if not client_secret:
        missing.append("CLIENT_SECRET")

    if missing:
        raise KeycloakConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Please check your .env file."
        )

    return keycloak_url, client_id, client_secret


# Initialize the Keycloak client
# We do this at module level so it's available to all tool functions
try:
    keycloak_url, client_id, client_secret = validate_environment()
    keycloak_client = KeycloakClient(
        base_url=keycloak_url,
        client_id=client_id,
        client_secret=client_secret,
    )
    logger.info("Keycloak client initialized successfully")
except KeycloakConfigError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize Keycloak client: {e}")
    sys.exit(1)


# =============================================================================
# MCP Tool Definitions
# =============================================================================
# Tools are the functions that AI models can call. Each tool is decorated
# with @mcp.tool() and should have a clear docstring explaining what it does.


@mcp.tool()
def get_realms() -> list[dict]:
    """Get a list of all realms from the Keycloak server.

    A realm in Keycloak is a space where you manage users, credentials,
    roles, and groups. A realm is isolated from other realms.

    Returns:
        A list of realm objects, each containing realm information like:
        - id: Unique identifier
        - realm: Realm name
        - displayName: Human-readable name
        - enabled: Whether the realm is active

    Example response:
        [
            {
                "id": "master",
                "realm": "master",
                "displayName": "Keycloak",
                "enabled": true
            }
        ]

    Note:
        This is a synchronous function, not async. FastMCP handles both
        sync and async functions correctly.
    """
    try:
        realms = keycloak_client.get_realms()
        logger.info(f"Retrieved {len(realms)} realms")
        # Convert Pydantic models to dictionaries for JSON serialization
        return [realm.model_dump(exclude_none=True) for realm in realms]
    except Exception as e:
        logger.error(f"Failed to get realms: {e}")
        # Re-raise the exception so the MCP client gets proper error info
        raise


@mcp.tool()
def get_users(realm: str, max_users: int = 100) -> list[dict]:
    """Get a list of users from a specific realm.

    Args:
        realm: The name of the realm to get users from (e.g., "master")
        max_users: Maximum number of users to return (default: 100)

    Returns:
        A list of user objects, each containing:
        - id: Unique user identifier (UUID)
        - username: User's username
        - email: User's email address
        - firstName: User's first name
        - lastName: User's last name
        - enabled: Whether the user account is active

    Example usage:
        get_users("master", 50)

    Example response:
        [
            {
                "id": "8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
                "username": "john.doe",
                "email": "john.doe@example.com",
                "firstName": "John",
                "lastName": "Doe",
                "enabled": true
            }
        ]

    Raises:
        KeycloakAPIError: If the realm doesn't exist or request fails
    """
    try:
        users = keycloak_client.get_users(realm=realm, max_users=max_users)
        logger.info(f"Retrieved {len(users)} users from realm '{realm}'")
        # Convert Pydantic models to dictionaries for JSON serialization
        return [user.model_dump(exclude_none=True) for user in users]
    except Exception as e:
        logger.error(f"Failed to get users from realm '{realm}': {e}")
        raise


@mcp.tool()
def get_user_info(realm: str, user_id: str) -> dict:
    """Get detailed information about a specific user.

    Args:
        realm: The realm the user belongs to
        user_id: The unique ID of the user (UUID format, not username!)
                 You can get this from the get_users() tool.

    Returns:
        A detailed user object containing all user attributes

    Example usage:
        get_user_info("master", "8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d")

    Example response:
        {
            "id": "8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
            "username": "john.doe",
            "email": "john.doe@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "enabled": true,
            "emailVerified": false,
            "createdTimestamp": 1609459200000,
            "attributes": {...}
        }

    Raises:
        KeycloakAPIError: If the user or realm doesn't exist
    """
    try:
        user = keycloak_client.get_user_info(realm=realm, user_id=user_id)
        logger.info(f"Retrieved info for user '{user_id}' in realm '{realm}'")
        # Convert Pydantic model to dictionary for JSON serialization
        return user.model_dump(exclude_none=True)
    except Exception as e:
        logger.error(f"Failed to get user info for '{user_id}' in realm '{realm}': {e}")
        raise


def main() -> None:
    """Main entry point for the MCP server.

    This function starts the FastMCP server using stdio transport,
    which means it communicates via standard input/output. This is
    the standard way MCP servers communicate with clients.
    """
    logger.info("Starting Keycloak MCP server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
