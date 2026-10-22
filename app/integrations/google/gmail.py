import json
import logging

import httpx

logger = logging.getLogger(__name__)

async def get_messages_list(access_token: str,
                            client: httpx.AsyncClient) -> dict:

    response = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages",
                                headers={"Authorization": f"Bearer {access_token}"},
                                timeout=10.0,
                                params={"maxResults": 5})
    response.raise_for_status()
    try:
        payload = response.json()
    except json.decoder.JSONDecodeError:
        logger.exception("Failed to decode Gmail messages list")
        raise

    if not isinstance(payload, dict):
        raise TypeError("Invalid Gmail response: Expected dictionary")

    return payload

async def get_message(
    message_id: str,
    access_token: str,
    client: httpx.AsyncClient,
) -> dict:
    response = await client.get(f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                                headers={"Authorization": f"Bearer {access_token}"},
                                timeout=10.0,
                                params={"format": "full"})
    response.raise_for_status()

    try:
        payload = response.json()
    except json.decoder.JSONDecodeError:
        logger.exception("Failed to decode gmail message")
        raise

    if not isinstance(payload, dict):
        raise TypeError("Invalid response type")

    return payload
