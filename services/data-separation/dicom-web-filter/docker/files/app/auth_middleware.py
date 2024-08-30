import httpx
import jwt
from jwt import PyJWKClient, InvalidTokenError
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config_url: str, client_id: str):
        super().__init__(app)
        self.config_url = config_url
        self.client_id = client_id
        self.jwks_url = None
        self.issuer = None
        self.jwks_client = None

    async def load_openid_config(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(self.config_url)
            response.raise_for_status()
            openid_config = response.json()
            self.jwks_url = openid_config["jwks_uri"]
            self.issuer = openid_config["issuer"]
            self.jwks_client = PyJWKClient(self.jwks_url)

    async def authenticate(self, token: str):
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

        await self.authenticate(token)

        response = await call_next(request)
        return response
