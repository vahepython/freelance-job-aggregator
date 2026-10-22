import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException
from starlette import status

from app.db.models.google_account import GoogleAccount
from app.core.encryption import decrypt_refresh_token

from app.integrations.google.oauth import refresh_access_token

async def get_gmail_access_token(user_id: int,
                                 session: AsyncSession,
                                 client: httpx.AsyncClient) -> str:
    google_acc_query = select(GoogleAccount).where(GoogleAccount.user_id == user_id)
    google_acc = await session.scalar(google_acc_query)

    if google_acc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gmail account not connected"
                            )

    enc_refresh_token = google_acc.encrypted_refresh_token
    if enc_refresh_token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No refresh token found"
                            )
    decoded_refresh_token = decrypt_refresh_token(enc_refresh_token)
    new_access_token = await refresh_access_token(client=client, refresh_token=decoded_refresh_token)
    return new_access_token
