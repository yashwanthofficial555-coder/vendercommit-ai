from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session
from .database import get_db
from .config import get_settings
from .models import User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not get_settings().auth_required:
        from sqlalchemy import select
        user = db.scalar(select(User).where(User.role == 'admin', User.is_active == True).limit(1))
        if not user:
            raise HTTPException(status_code=503, detail='Local demo administrator is unavailable')
        return user
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    if not credentials:
        raise error
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload['sub'])
    except (ExpiredSignatureError, InvalidTokenError, ValueError, KeyError):
        raise error
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise error
    return user

def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail='Insufficient permissions')
        return user
    return dependency
