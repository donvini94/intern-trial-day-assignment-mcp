import logging
from typing import Any

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KeycloakClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None

    def _get_access_token(self) -> str:
        token_endpoint = f"{self.base_url}/realms/master/protocol/openid-connect/token"

        client_credentials = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            response = requests.post(token_endpoint, data=client_credentials)
            response.raise_for_status()
            token_data = response.json()
            return token_data["access_token"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise Exception(f"Keycloak authentication failed: {str(e)}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        if not self.access_token:
            self.access_token = self._get_access_token()

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.request(method, url, headers=headers, timeout=10)
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

        except requests.exceptions.HTTPError as e:
            # try again in case of unauthorized error
            if e.response.status_code == 401:
                self.access_token = self._get_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.request(method, url, headers=headers, timeout=10)
                response.raise_for_status()
                return response.json() if response.status_code != 204 else None
            else:
                logger.error(f"Keycloak API error: {e}")
                raise Exception(f"Keycloak API request failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise Exception(f"Failed to communicate with Keycloak: {str(e)}")

    def get_realms(self) -> list:
        return self._make_request("GET", "/admin/realms")
