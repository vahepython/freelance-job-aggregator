import logging
import secrets
import json

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from starlette import status
from sqlalchemy.ext.asyncio import AsyncSession

from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError
)

from urllib.parse import urlencode

from redis.asyncio import Redis
from app.core.config import settings
from app.db.base import db_session

from app.db.models.user import User
from app.services.utilities import get_redis

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
            detail="Сервис временно недоступен. Попробуй позже.",
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
            detail="Сервис временно недоступен. Попробуй позже.",
        )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.readonly",
        "access_type": "offline",
        "state": state,
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
