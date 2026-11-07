import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Commitment, MemoryItem, Supplier, User
from ..repositories.base import audit
from ..schemas import APIResponse, MemoryCreate, MemoryOut
from ..services.intelligence import serialize_commitment
from ..services.memory import MemoryError, MemoryService
from ..services.memory_intelligence import compare_memory_decision, supplier_memory_insights

router = APIRouter(prefix='/memory', tags=['Hindsight Memory'])

@router.post('/retain', response_model=APIResponse[MemoryOut], status_code=201)
def retain(payload: MemoryCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    if not db.get(Supplier, payload.supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    item = MemoryService().retain(db, payload.supplier_id, payload.content, payload.provenance)
    audit(db, user_id=user.id, action='retain', entity_type='memory', entity_id=item.id, details={'supplier_id': item.supplier_id, 'mode': item.provenance}, request=request)
    db.commit(); db.refresh(item)
    return {'data': item, 'meta': {'mode': MemoryService().mode, 'ai_generated': False}}

@router.get('/recall/{supplier_id}')
def recall(supplier_id: int, query: str = Query(default='', max_length=500), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    result = MemoryService().recall(db, supplier_id, query)
    result['items'] = [item if isinstance(item, dict) else MemoryOut.model_validate(item).model_dump() for item in result['items']]
    return {'data': result}

@router.get('/history/{supplier_id}')
def commitment_history(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    items = db.scalars(select(Commitment).where(Commitment.supplier_id == supplier_id).order_by(Commitment.created_at.desc())).all()
    return {'data': [serialize_commitment(c) for c in items], 'meta': {'source': 'operational_database'}}

@router.get('/status')
def status(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {'data': MemoryService().status(db)}

@router.get('/insights/{supplier_id}')
def insights(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    return {'data': supplier_memory_insights(db, supplier_id)}

@router.get('/compare/{supplier_id}')
def compare(supplier_id: int, scenario: str = Query('price_negotiation', pattern='^(price_negotiation|delivery_planning)$'), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail='Supplier not found')
    service = MemoryService()
    recalled = service.recall(db, supplier_id, scenario.replace('_',' ') if service.mode == 'CLOUD' else '')
    evidence = recalled['items']
    normalized = [item if isinstance(item, dict) else {'id':item.id,'title':json.loads(item.provenance or '{}').get('title','Retained source record'),'category':json.loads(item.provenance or '{}').get('category','source_record'),'content':item.content,'source_interaction_id':json.loads(item.provenance or '{}').get('source_interaction_id'),'learned_at':item.created_at,'provenance':json.loads(item.provenance or '{}'),'sync_status':item.sync_status} for item in evidence]
    return {'data': compare_memory_decision(db, supplier_id, scenario, normalized, {'source':recalled['source'],'cloud_retrieved':recalled['cloud_retrieved'],'warning':recalled['warning']})}

@router.get('/health')
def cloud_health(supplier_id: int = 1, _: User = Depends(get_current_user)):
    return {'data': MemoryService().health(supplier_id)}

@router.post('/{memory_id}/retry', response_model=APIResponse[MemoryOut])
def retry(memory_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_roles('admin','procurement'))):
    item = db.get(MemoryItem, memory_id)
    if not item: raise HTTPException(status_code=404, detail='Memory item not found')
    try: MemoryService().retry(item)
    except MemoryError as exc: raise HTTPException(status_code=409, detail=str(exc))
    audit(db, user_id=user.id, action='retry_sync', entity_type='memory', entity_id=item.id, details={'status': item.sync_status}, request=request)
    db.commit(); db.refresh(item)
    return {'data': item}
