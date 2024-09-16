import logging

import httpx
import jwt
from fastapi import HTTPException, Request
from jwt import InvalidTokenError, PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authenticating requests using OpenID Connect.

    Args:
        BaseHTTPMiddleware (class): The base class for HTTP middleware.
    """

    def __init__(self, app, config_url: str, client_id: str):
        super().__init__(app)
        self.config_url = config_url
        self.client_id = client_id
        self.jwks_url = None
        self.issuer = None
        self.jwks_client = None

    async def load_openid_config(self):
        """Load OpenID configuration from the provided URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.config_url)
            response.raise_for_status()
            openid_config = response.json()
            self.jwks_url = openid_config["jwks_uri"]
            self.issuer = openid_config["issuer"]
            self.jwks_client = PyJWKClient(self.jwks_url)

    async def authenticate(self, token: str):
        """Authenticate the user using the provided token.

        Args:
            token (str): The token to authenticate the user with.

        Raises:
            HTTPException: If the token is invalid or the claims are missing.

        Returns:
            dict: The payload of the token.
        """
        if not self.jwks_url or not self.issuer or not self.jwks_client:
            await self.load_openid_config()

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                key=signing_key.key,
                audience=self.client_id,
                issuer=self.issuer,
                algorithms=["RS256"],
            )
            return payload
        except (InvalidTokenError, KeyError) as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(status_code=403, detail="Invalid token or claims")

    async def dispatch(self, request: Request, call_next):
        """Dispatch the request to the next middleware in the stack.

        Args:
            request (Request): The incoming request.
            call_next (function): The next middleware in the stack or the endpoint.

        Raises:
            HTTPException: If the token is missing or invalid.

        Returns:
            Response: The response from the next middleware or the endpoint.
        """
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            # Fallback to other headers if Authorization is missing or invalid
            token = request.headers.get("x-forwarded-access-token")

        if not token:
            raise HTTPException(
                status_code=403, detail="Authorization token missing or invalid"
            )

        payload = await self.authenticate(token)

        # Check if the user is an admin
        if "admin" in payload.get("realm_access", {}).get("roles", []):
            # Set a parameter to indicate that the request comes from an admin
            request.scope["admin"] = True
        else:
            request.scope["admin"] = False

        response = await call_next(request)
        return response
