import logging
import secrets
import json

import httpx
from fastapi import APIRouter, HTTPException, Query, Depends, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError
)

from urllib.parse import urlencode

from redis.asyncio import Redis
from app.core.config import settings
from app.db.base import db_session
from app.db.models.google_account import GoogleAccount

from app.db.models.user import User
from app.services.utilities import get_redis

from app.services.utilities import get_async_client
from app.integrations.google.oauth import (
    exchange_code_for_tokens,
    InvalidAuthorizationCodeError, GoogleOAuthError
)
from app.core.encryption import encrypt_refresh_token
from app.services.utilities import notify_gmail_connected

logger = logging.getLogger(__name__)
oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])

@oauth_router.get("/google/start")
async def oauth_google_start(ticket: str =  Query(...), session: AsyncSession = Depends(db_session),
                             redis_client: Redis = Depends(get_redis)):
    try:
        user_id = await redis_client.get(f"gmail_connect:{ticket}")
    except (RedisTimeoutError, RedisConnectionError):
        logger.exception("Error connecting to Redis: ")
        raise HTTPException(
            status_code=503,
            detail="Сервис временно недоступен. Попробуй позже. \n"
                   "Service temporary unavailable. Try later.",
        )

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid ticket. Return to Telegram "
                                    "and try again.\n"
                                    "Ссылка недействительна. Вернись в Telegram")

    user_id = int(user_id)
    postgres_user = await session.get(User, user_id)
    if postgres_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found")

    state = secrets.token_urlsafe(32)
    browser_session_id = secrets.token_urlsafe(32)
    oauth_attempt = {
        "user_id": int(user_id),
        "browser_session_id": browser_session_id,
    }
    try:
        await redis_client.set(
            name=f"oauth_state:{state}",
            value=json.dumps(oauth_attempt),
            ex=600,
        )

    except (RedisConnectionError, RedisTimeoutError):
        logger.exception("Failed to save OAuth attempt")
        raise HTTPException(
            status_code=503,
            detail="Сервис временно недоступен. Попробуй позже. \n"
                   "Server temporary unavailable. Try later.",
        )

    params = {
        "client_id": settings.client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.readonly",
        "access_type": "offline",
        "state": state,
        "prompt": "consent"
    }

    authorization_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            + urlencode(params)
    )

    response = RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )

    response.set_cookie(
        key="oauth_browser_session",
        value=browser_session_id,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=False,
    )

    return response


@oauth_router.get("/google/callback")
async def get_google_callback(
    state: str = Query(...),
    code: str | None = Query(None),
    error: str | None = Query(None),
    browser_id: str | None = Cookie(
        None,
        alias="oauth_browser_session",
    ),
    redis_client: Redis = Depends(get_redis),
        client: httpx.AsyncClient = Depends(get_async_client),
        session: AsyncSession = Depends(db_session)

):
    state_key = f"oauth_state:{state}"

    try:
        info_json = await redis_client.get(state_key)
    except (RedisTimeoutError, RedisConnectionError):
        logger.exception("Failed to read OAuth attempt")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис временно недоступен. Попробуй позже. \n"
                   "Service unavailable now. Try again later",
        )

    if info_json is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth attempt expired or invalid.",
        )

    try:
        info = json.loads(info_json)
    except json.JSONDecodeError:
        logger.exception("Invalid OAuth attempt JSON")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обработать OAuth-попытку.",
        )

    if not isinstance(info, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth attempt data.",
        )

    expected_browser_id = info.get("browser_session_id")

    if not isinstance(expected_browser_id, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth browser session data.",
        )

    if not browser_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Browser session cookie is missing.",
        )

    if not secrets.compare_digest(browser_id, expected_browser_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Browser session mismatch.",
        )

    if error is None and not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is missing.",
        )

    try:
        claimed_attempt = await redis_client.getdel(state_key)
    except (RedisTimeoutError, RedisConnectionError):
        logger.exception("Failed to consume OAuth attempt")
        raise HTTPException(
            status_code=503,
            detail="Сервис временно недоступен. Попробуй позже.",
        )

    if claimed_attempt is None:
        raise HTTPException(
            status_code=400,
            detail="OAuth attempt expired or already used.",
        )

    if error is not None:
        detail = (
            "Подключение Gmail отменено."
            if error == "access_denied"
            else "Google вернул ошибку подключения."
        )
        response = JSONResponse(
            status_code=400,
            content={"detail": detail},
        )
    else:
        try:
            user_id = info["user_id"]

            user = await session.get(User, user_id)
            if user is None:
                raise HTTPException(
                    status_code=404,
                    detail="User not found.",
                )

            tokens = await exchange_code_for_tokens(
                code=code,
                client=client,
            )

            access_token = tokens["access_token"]
            refresh_token = tokens.get("refresh_token")
            granted_scopes = tokens["scope"].split()

            profile_response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=10.0,
            )

            if profile_response.status_code != 200:
                raise GoogleOAuthError("Failed to get Gmail profile.")

            profile = profile_response.json()

            if not isinstance(profile, dict):
                raise GoogleOAuthError("Invalid Gmail profile response.")

            gmail_email = profile.get("emailAddress")

            if not isinstance(gmail_email, str) or not gmail_email.strip():
                raise GoogleOAuthError("Gmail email address is missing.")

            existing_account = await session.scalar(
                select(GoogleAccount).where(
                    GoogleAccount.user_id == user_id
                )
            )

            if refresh_token:
                encrypted_refresh_token = encrypt_refresh_token(
                    refresh_token
                )
            elif (
                    existing_account is not None
                    and existing_account.email.casefold()
                    == gmail_email.casefold()
                    and existing_account.encrypted_refresh_token
            ):
                encrypted_refresh_token = (
                    existing_account.encrypted_refresh_token
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Google не выдал refresh token. "
                        "Подключение не сохранено. Нужно повторное "
                        "подключение с запросом согласия."
                    ),
                )

            if existing_account is None:
                google_account = GoogleAccount(
                    user_id=user_id,
                    email=gmail_email,
                    encrypted_refresh_token=encrypted_refresh_token,
                    granted_scopes=granted_scopes,
                )
                session.add(google_account)
            else:
                existing_account.email = gmail_email
                existing_account.encrypted_refresh_token = (
                    encrypted_refresh_token
                )
                existing_account.granted_scopes = granted_scopes

            await session.commit()
            await notify_gmail_connected(chat_id=user.chat_id)

        except InvalidAuthorizationCodeError:
            response = JSONResponse(
                status_code=400,
                content={
                    "detail": (
                        "Код недействителен. "
                        "Начни подключение Gmail заново."
                    )
                },
            )

        except GoogleOAuthError:
            logger.warning("Google OAuth operation failed")
            response = JSONResponse(
                status_code=502,
                content={
                    "detail": "Не удалось подключить Gmail через Google."
                },
            )

        except httpx.RequestError:
            logger.warning("Gmail profile request failed")
            response = JSONResponse(
                status_code=502,
                content={
                    "detail": "Не удалось получить Gmail-профиль."
                },
            )

        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Invalid Gmail profile JSON")
            response = JSONResponse(
                status_code=502,
                content={
                    "detail": "Google вернул некорректный ответ профиля."
                },
            )

        except SQLAlchemyError:
            await session.rollback()
            logger.exception("Failed to save Google account")
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "Не удалось сохранить подключение Gmail."
                },
            )

        except HTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        else:
            response = JSONResponse(
                content={
                    "detail": (
                        "Gmail успешно подключён. Вернись в Telegram. \n"
                        "Gmail successfully connected. Return to telegram. "
                    )
                },
            )

    response.delete_cookie("oauth_browser_session")
    return response
