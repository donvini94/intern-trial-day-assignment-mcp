import os

import requests
from dotenv import load_dotenv

# What we want to achieve here is just to test connectivity to Keycloak
# First, we want to find out which endpoint to use for authentication of our MCP server
# Usually, the documentation is very clear about the available endpoints and what they do
# OpenID Connect also standardizes a lot
# The specific endpoints are listed https://www.keycloak.org/securing-apps/oidc-layers

# Never keep secrets in your code!
load_dotenv()
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# OpenID Connect Providers usually publish their configuration under the following URL
# If we deal with bad documentation, we can get the endpoints from here
OIDC_CONFIG_URL = ".well-known/openid-configuration"
OIDC_CONFIG = requests.get(f"{KEYCLOAK_URL}/realms/master/{OIDC_CONFIG_URL}").json()
# This then shows us that there are, amongst others, authorization and token endpoints
endpoints = {k: v for k, v in OIDC_CONFIG.items() if k.endswith("endpoint")}

# For the purposes of this assignment, we will continue with the token endpoint
TOKEN_ENDPOINT = endpoints["token_endpoint"]

# Now let's test that we can actually authenticate ourselves with the given credentials at the keycloak server
# Remember, we want to authenticate as a client, not as a user, hence we use the client credentials grant type instead of the authorization code grant type
client_credentials = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

# https://www.keycloak.org/docs/latest/authorization_services/index.html#_authentication_methods
response = requests.post(TOKEN_ENDPOINT, client_credentials)
access_token = response.json()["access_token"]

# https://www.keycloak.org/docs-api/latest/rest-api/index.html#_realms_admin
realms_url = f"{KEYCLOAK_URL}/admin/realms"
headers = {"Authorization": f"Bearer {access_token}"}
realms = requests.get(realms_url, headers=headers)

print(realms.json())
print(f"Found {len(realms.json())} realms")
