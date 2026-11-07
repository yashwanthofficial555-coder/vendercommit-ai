from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_roles
from ..models import AuditLog, User

router = APIRouter(prefix='/audit-logs', tags=['Audit'])

@router.get('')
def list_audit_logs(entity_type: str | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(require_roles('admin'))):
    statement = select(AuditLog)
    if entity_type: statement = statement.where(AuditLog.entity_type == entity_type)
    items = db.scalars(statement.order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return {'data': [{'id': a.id, 'user_id': a.user_id, 'action': a.action, 'entity_type': a.entity_type, 'entity_id': a.entity_id, 'details': a.details, 'ip_address': a.ip_address, 'created_at': a.created_at} for a in items]}
