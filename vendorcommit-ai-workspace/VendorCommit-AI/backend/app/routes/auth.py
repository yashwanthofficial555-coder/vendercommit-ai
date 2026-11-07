from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import User
from ..repositories.base import audit
from ..schemas import APIResponse, LoginRequest, Token, UserCreate, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix='/auth', tags=['Authentication'])

@router.post('/login', response_model=APIResponse[Token])
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    token, expires = create_access_token(user.id, user.role)
    audit(db, user_id=user.id, action='login', entity_type='user', entity_id=user.id, request=request)
    db.commit()
    return {'data': Token(access_token=token, expires_in=expires)}

@router.get('/me', response_model=APIResponse[UserOut])
def me(user: User = Depends(get_current_user)):
    return {'data': user}

@router.post('/users', response_model=APIResponse[UserOut], status_code=201)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_roles('admin'))):
    if db.scalar(select(User).where(func.lower(User.email) == payload.email.lower())):
        raise HTTPException(status_code=409, detail='A user with this email already exists')
    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user); db.flush()
    audit(db, user_id=admin.id, action='create', entity_type='user', entity_id=user.id, details={'role': user.role}, request=request)
    db.commit(); db.refresh(user)
    return {'data': user}
