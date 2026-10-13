from json import JSONDecodeError
from typing import Any

import httpx

from app.core.config import settings


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GoogleOAuthError(Exception):
    pass


class InvalidAuthorizationCodeError(GoogleOAuthError):
    pass


async def exchange_code_for_tokens(
    code: str,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    if not code:
        raise InvalidAuthorizationCodeError(
            "Authorization code is missing. Start OAuth again."
        )

    payload = {
        "code": code,
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "redirect_uri": settings.redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=payload,
            timeout=10.0,
        )
    except httpx.TimeoutException:
        raise GoogleOAuthError("Google token request timed out.") from None
    except httpx.RequestError:
        raise GoogleOAuthError("Could not contact Google.") from None

    try:
        tokens = response.json()
    except (JSONDecodeError, UnicodeDecodeError):
        raise GoogleOAuthError("Google returned invalid JSON.") from None

    if not isinstance(tokens, dict):
        raise GoogleOAuthError("Google returned an invalid token response.")

    if response.status_code != 200:
        if tokens.get("error") == "invalid_grant":
            raise InvalidAuthorizationCodeError(
                "Authorization code is invalid. Start OAuth again."
            )
        raise GoogleOAuthError(
            f"Google rejected the token exchange (HTTP {response.status_code})."
        )

    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthError("Google did not return a valid access token.")

    token_type = tokens.get("token_type")
    if not isinstance(token_type, str) or token_type.lower() != "bearer":
        raise GoogleOAuthError("Google returned an unsupported token type.")

    refresh_token = tokens.get("refresh_token")
    if refresh_token is not None and (
        not isinstance(refresh_token, str) or not refresh_token
    ):
        raise GoogleOAuthError("Google returned an invalid refresh token.")

    scopes = tokens.get("scope", "")
    if not isinstance(scopes, str) or GMAIL_READONLY_SCOPE not in scopes.split():
        raise GoogleOAuthError("Gmail read permission was not granted.")

    return tokens