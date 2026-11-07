from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Interaction, Supplier, User
from ..repositories.base import audit, pagination_meta
from ..schemas import APIResponse, InteractionCreate, InteractionOut, InteractionUpdate
from ..services.learning import learn_from_interaction

router = APIRouter(prefix='/interactions', tags=['Interactions'])

@router.get('', response_model=APIResponse[list[InteractionOut]])
def list_interactions(supplier_id: int | None = None, interaction_type: str | None = Query(default=None, pattern='^(call|email|meeting|delivery|note|negotiation)$'), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    statement = select(Interaction)
    if supplier_id: statement = statement.where(Interaction.supplier_id == supplier_id)
    if interaction_type: statement = statement.where(Interaction.interaction_type == interaction_type)
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    items = db.scalars(statement.order_by(Interaction.occurred_at.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {'data': items, 'meta': pagination_meta(total, page, page_size)}

@router.post('', response_model=APIResponse[InteractionOut], status_code=201)
def create_interaction(payload: InteractionCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    if not db.get(Supplier, payload.supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    values = payload.model_dump(); values['occurred_at'] = values['occurred_at'] or datetime.now(timezone.utc)
    interaction = Interaction(**values, author_id=user.id)
    db.add(interaction); db.flush()
    memory = learn_from_interaction(db, interaction)
    audit(db, user_id=user.id, action='create', entity_type='interaction', entity_id=interaction.id, details={'memory_item_id': memory.id, 'memory_status': memory.sync_status}, request=request)
    db.commit(); db.refresh(interaction)
    return {'data': interaction, 'meta': {'memory_item_id': memory.id, 'memory_status': memory.sync_status, 'retention_method': 'verbatim_source_retention', 'ai_generated': False}}

@router.get('/{interaction_id}', response_model=APIResponse[InteractionOut])
def get_interaction(interaction_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(Interaction, interaction_id)
    if not item: raise HTTPException(status_code=404, detail='Interaction not found')
    return {'data': item}

@router.patch('/{interaction_id}', response_model=APIResponse[InteractionOut])
def update_interaction(interaction_id: int, payload: InteractionUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    item = db.get(Interaction, interaction_id)
    if not item: raise HTTPException(status_code=404, detail='Interaction not found')
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items(): setattr(item, key, value)
    audit(db, user_id=user.id, action='update', entity_type='interaction', entity_id=item.id, details={'fields': list(changes)}, request=request)
    db.commit(); db.refresh(item)
    return {'data': item}

@router.delete('/{interaction_id}', status_code=204)
def delete_interaction(interaction_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin'))):
    item = db.get(Interaction, interaction_id)
    if not item: raise HTTPException(status_code=404, detail='Interaction not found')
    audit(db, user_id=user.id, action='delete', entity_type='interaction', entity_id=item.id, request=request)
    db.delete(item); db.commit()
