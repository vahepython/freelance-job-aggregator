import asyncio
from contextlib import asynccontextmanager

import httpx
from sqlalchemy import select

from app.db.base import db_session
from app.db.models.user import User
from app.integrations.google.gmail import get_message, get_messages_list
from app.services.gmail_connection import get_gmail_access_token


async def main():
    try:
        telegram_id = int(input("Enter your Telegram ID: "))
    except ValueError:
        print("Telegram ID must be an integer.")
        return

    session_context = asynccontextmanager(db_session)

    async with session_context() as session:
        user_id = await session.scalar(
            select(User.id).where(User.telegram_id == telegram_id)
        )

        if user_id is None:
            print("User not found. Send /start to the bot first.")
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            access_token = await get_gmail_access_token(
                user_id=user_id,
                session=session,
                client=client,
            )

            payload = await get_messages_list(
                access_token=access_token,
                client=client,
            )

            messages = payload.get("messages", [])

            if not messages:
                print("No messages found.")
                return

            message = await get_message(
                message_id=messages[0]["id"],
                access_token=access_token,
                client=client,
            )

            headers = {
                header["name"].casefold(): header["value"]
                for header in message.get("payload", {}).get("headers", [])
            }

            print("From:", headers.get("from", "Unknown sender"))
            print("Subject:", headers.get("subject", "No subject"))
            print("Snippet:", message.get("snippet", ""))


if __name__ == "__main__":
    asyncio.run(main())