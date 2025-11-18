import logging
import os
import sys

import mcp.types as types
from dotenv import load_dotenv
from fastmcp import FastMCP

from client import KeycloakClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("keycloak-werki")
load_dotenv()

try:
    keycloak_client = KeycloakClient(
        base_url=os.getenv("KEYCLOAK_URL", ""),
        client_id=os.getenv("CLIENT_ID", ""),
        client_secret=os.getenv("CLIENT_SECRET", ""),
    )
except Exception as e:
    logger.error(f"Failed to initialize Keycloak client: {e}")
    sys.exit(1)


@mcp.tool()
async def get_realms() -> list:
    """Get keycloak realms"""
    return keycloak_client.get_realms()


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
