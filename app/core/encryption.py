from cryptography.fernet import Fernet

from app.core.config import settings


fernet = Fernet(settings.encryption_key.encode())


def encrypt_refresh_token(refresh_token: str) -> str:
    return fernet.encrypt(refresh_token.encode()).decode()

def decrypt_refresh_token(refresh_token: str) -> str:
    return fernet.decrypt(refresh_token.encode()).decode()