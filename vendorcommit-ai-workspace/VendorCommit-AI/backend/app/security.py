from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from .config import get_settings

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires = timedelta(minutes=settings.access_token_minutes)
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'role': role, 'iat': now, 'exp': now + expires, 'type': 'access'}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), int(expires.total_seconds())

def decode_access_token(token: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get('type') != 'access':
        raise jwt.InvalidTokenError('Invalid token type')
    return payload
