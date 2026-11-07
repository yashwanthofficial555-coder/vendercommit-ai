import re
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import PerformanceHistory, Supplier, User
from ..repositories.base import audit, pagination_meta
from ..schemas import APIResponse, PerformanceOut, StatusUpdate, SupplierCreate, SupplierOut, SupplierUpdate
from ..services.intelligence import record_performance, supplier_out

router = APIRouter(prefix='/suppliers', tags=['Suppliers'])
def normalize(name): return re.sub(r'[^a-z0-9]+', '', name.lower())

@router.get('', response_model=APIResponse[list[SupplierOut]])
def list_suppliers(search: str = Query(default='', max_length=200), status: str | None = Query(default=None, pattern='^(active|inactive|onboarding|suspended)$'), category: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), sort: str = Query('name', pattern='^(name|created_at|updated_at|status)$'), order: str = Query('asc', pattern='^(asc|desc)$'), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    statement = select(Supplier)
    if search:
        safe = search.replace('%', r'\%').replace('_', r'\_')
        statement = statement.where(or_(Supplier.name.ilike(f'%{safe}%', escape='\\'), Supplier.contact_name.ilike(f'%{safe}%', escape='\\'), Supplier.category.ilike(f'%{safe}%', escape='\\')))
    if status: statement = statement.where(Supplier.status == status)
    if category: statement = statement.where(Supplier.category == category)
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    statement = statement.order_by(desc(getattr(Supplier, sort)) if order == 'desc' else asc(getattr(Supplier, sort))).offset((page-1)*page_size).limit(page_size)
    suppliers = db.scalars(statement).unique().all()
    data = [supplier_out(db, s) for s in suppliers]
    db.commit()
    return {'data': data, 'meta': pagination_meta(total, page, page_size)}

@router.post('', response_model=APIResponse[SupplierOut], status_code=201)
def create_supplier(payload: SupplierCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    normalized = normalize(payload.name)
    if db.scalar(select(Supplier).where(Supplier.normalized_name == normalized)):
        raise HTTPException(status_code=409, detail='A supplier with the same normalized name already exists')
    if payload.email and db.scalar(select(Supplier).where(func.lower(Supplier.email) == payload.email.lower(), Supplier.email != '')):
        raise HTTPException(status_code=409, detail='A supplier with this email already exists')
    values = payload.model_dump()
    values['email'] = str(payload.email)
    supplier = Supplier(**values, normalized_name=normalized)
    db.add(supplier); db.flush()
    audit(db, user_id=user.id, action='create', entity_type='supplier', entity_id=supplier.id, request=request)
    db.commit()
    return {'data': supplier_out(db, supplier)}

@router.get('/{supplier_id}', response_model=APIResponse[SupplierOut])
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier: raise HTTPException(status_code=404, detail='Supplier not found')
    data = supplier_out(db, supplier); db.commit()
    return {'data': data}

@router.patch('/{supplier_id}', response_model=APIResponse[SupplierOut])
def update_supplier(supplier_id: int, payload: SupplierUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    supplier = db.get(Supplier, supplier_id)
    if not supplier: raise HTTPException(status_code=404, detail='Supplier not found')
    changes = payload.model_dump(exclude_unset=True)
    if 'name' in changes:
        normalized = normalize(changes['name'])
        duplicate = db.scalar(select(Supplier).where(Supplier.normalized_name == normalized, Supplier.id != supplier_id))
        if duplicate: raise HTTPException(status_code=409, detail='A supplier with the same normalized name already exists')
        supplier.normalized_name = normalized
    if changes.get('email'):
        duplicate = db.scalar(select(Supplier).where(func.lower(Supplier.email) == str(changes['email']).lower(), Supplier.id != supplier_id, Supplier.email != ''))
        if duplicate: raise HTTPException(status_code=409, detail='A supplier with this email already exists')
    for key, value in changes.items(): setattr(supplier, key, str(value) if key == 'email' else value)
    audit(db, user_id=user.id, action='update', entity_type='supplier', entity_id=supplier.id, details={'fields': list(changes)}, request=request)
    db.commit()
    return {'data': supplier_out(db, supplier)}

@router.patch('/{supplier_id}/status', response_model=APIResponse[SupplierOut])
def update_status(supplier_id: int, payload: StatusUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    supplier = db.get(Supplier, supplier_id)
    if not supplier: raise HTTPException(status_code=404, detail='Supplier not found')
    old = supplier.status; supplier.status = payload.status
    audit(db, user_id=user.id, action='status_change', entity_type='supplier', entity_id=supplier.id, details={'from': old, 'to': payload.status}, request=request)
    db.commit()
    return {'data': supplier_out(db, supplier)}

@router.delete('/{supplier_id}', status_code=204)
def delete_supplier(supplier_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    supplier = db.get(Supplier, supplier_id)
    if not supplier: raise HTTPException(status_code=404, detail='Supplier not found')
    audit(db, user_id=user.id, action='delete', entity_type='supplier', entity_id=supplier.id, details={'name': supplier.name}, request=request)
    db.delete(supplier); db.commit()

@router.get('/{supplier_id}/performance', response_model=APIResponse[list[PerformanceOut]])
def performance_history(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    return {'data': db.scalars(select(PerformanceHistory).where(PerformanceHistory.supplier_id == supplier_id).order_by(PerformanceHistory.recorded_at.desc())).all()}

@router.post('/{supplier_id}/performance/snapshot', response_model=APIResponse[PerformanceOut], status_code=201)
def create_snapshot(supplier_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    snapshot = record_performance(db, supplier_id)
    if not snapshot: raise HTTPException(status_code=409, detail='Insufficient terminal commitments for a performance snapshot')
    audit(db, user_id=user.id, action='snapshot', entity_type='supplier', entity_id=supplier_id)
    db.commit(); db.refresh(snapshot)
    return {'data': snapshot}
