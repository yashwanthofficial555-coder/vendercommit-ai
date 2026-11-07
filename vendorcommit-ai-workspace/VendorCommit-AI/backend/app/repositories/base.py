import json
from fastapi import Request
from sqlalchemy.orm import Session
from ..models import AuditLog

def audit(db: Session, *, user_id: int | None, action: str, entity_type: str, entity_id: int | str = '', details: dict | None = None, request: Request | None = None):
    entry = AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=str(entity_id), details=json.dumps(details or {}, default=str), ip_address=request.client.host if request and request.client else '')
    db.add(entry)

def pagination_meta(total: int, page: int, page_size: int):
    return {'total': total, 'page': page, 'page_size': page_size, 'pages': (total + page_size - 1) // page_size}
