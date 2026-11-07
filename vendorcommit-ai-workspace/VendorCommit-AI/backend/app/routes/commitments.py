from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Commitment, Supplier, User
from ..repositories.base import audit, pagination_meta
from ..schemas import APIResponse, CommitmentCreate, CommitmentOut, CommitmentUpdate, VerificationRequest
from ..services.intelligence import refresh_commitment_statuses, serialize_commitment

router = APIRouter(prefix='/commitments', tags=['Commitments'])

@router.get('', response_model=APIResponse[list[CommitmentOut]])
def list_commitments(supplier_id: int | None = None, status: str | None = Query(default=None, pattern='^(pending|fulfilled|overdue|breached)$'), commitment_type: str | None = Query(default=None, pattern='^(price|delivery|quantity|quality|sla)$'), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), sort: str = Query('created_at', pattern='^(created_at|updated_at|deadline|current_value)$'), order: str = Query('desc', pattern='^(asc|desc)$'), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refresh_commitment_statuses(db)
    statement = select(Commitment)
    if supplier_id: statement = statement.where(Commitment.supplier_id == supplier_id)
    if status: statement = statement.where(Commitment.status == status)
    if commitment_type: statement = statement.where(Commitment.commitment_type == commitment_type)
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    statement = statement.order_by(desc(getattr(Commitment, sort)) if order == 'desc' else asc(getattr(Commitment, sort))).offset((page-1)*page_size).limit(page_size)
    data = [serialize_commitment(c) for c in db.scalars(statement).all()]
    db.commit()
    return {'data': data, 'meta': pagination_meta(total, page, page_size)}

@router.post('', response_model=APIResponse[CommitmentOut], status_code=201)
def create_commitment(payload: CommitmentCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    if not db.get(Supplier, payload.supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    commitment = Commitment(**payload.model_dump(), created_by_id=user.id)
    if commitment.status == 'fulfilled': commitment.fulfilled_at = datetime.now(timezone.utc)
    db.add(commitment); db.flush()
    audit(db, user_id=user.id, action='create', entity_type='commitment', entity_id=commitment.id, details={'supplier_id': commitment.supplier_id}, request=request)
    db.commit()
    return {'data': serialize_commitment(commitment)}

@router.get('/{commitment_id}', response_model=APIResponse[CommitmentOut])
def get_commitment(commitment_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    commitment = db.get(Commitment, commitment_id)
    if not commitment: raise HTTPException(status_code=404, detail='Commitment not found')
    return {'data': serialize_commitment(commitment)}

@router.patch('/{commitment_id}', response_model=APIResponse[CommitmentOut])
def update_commitment(commitment_id: int, payload: CommitmentUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    commitment = db.get(Commitment, commitment_id)
    if not commitment: raise HTTPException(status_code=404, detail='Commitment not found')
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items(): setattr(commitment, key, value)
    if changes.get('status') == 'fulfilled' and not commitment.fulfilled_at: commitment.fulfilled_at = datetime.now(timezone.utc)
    if commitment.status != 'fulfilled': commitment.fulfilled_at = None
    if changes.get('status') == 'pending' and commitment.deadline and commitment.deadline.replace(tzinfo=commitment.deadline.tzinfo or timezone.utc) < datetime.now(timezone.utc): commitment.status = 'overdue'
    commitment.verified_at = None; commitment.verified_by_id = None; commitment.verification_note = ''
    audit(db, user_id=user.id, action='update', entity_type='commitment', entity_id=commitment.id, details={'fields': list(changes)}, request=request)
    db.commit()
    return {'data': serialize_commitment(commitment)}

@router.post('/{commitment_id}/verify', response_model=APIResponse[CommitmentOut])
def verify_commitment(commitment_id: int, payload: VerificationRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    commitment = db.get(Commitment, commitment_id)
    if not commitment: raise HTTPException(status_code=404, detail='Commitment not found')
    if commitment.created_by_id == user.id: raise HTTPException(status_code=403, detail='Independent verification requires a different user')
    commitment.verified_at = datetime.now(timezone.utc); commitment.verified_by_id = user.id; commitment.verification_note = payload.note
    audit(db, user_id=user.id, action='verify', entity_type='commitment', entity_id=commitment.id, details={'note': payload.note}, request=request)
    db.commit()
    return {'data': serialize_commitment(commitment)}

@router.delete('/{commitment_id}', status_code=204)
def delete_commitment(commitment_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    commitment = db.get(Commitment, commitment_id)
    if not commitment: raise HTTPException(status_code=404, detail='Commitment not found')
    audit(db, user_id=user.id, action='delete', entity_type='commitment', entity_id=commitment.id, request=request)
    db.delete(commitment); db.commit()
