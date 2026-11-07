from collections import defaultdict
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..models import AuditLog, Commitment, Interaction, Supplier, User
from ..services.intelligence import refresh_commitment_statuses, supplier_metrics, upcoming_deadlines

router = APIRouter(prefix='/dashboard', tags=['Dashboard'])

@router.get('/executive')
def executive(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refresh_commitment_statuses(db)
    suppliers = db.scalars(select(Supplier)).all()
    commitments = db.scalars(select(Commitment)).all()
    interactions = db.scalars(select(Interaction)).all()
    by_supplier = defaultdict(list)
    for commitment in commitments: by_supplier[commitment.supplier_id].append(commitment)
    risk = {'low': 0, 'medium': 0, 'high': 0, 'unknown': 0}
    for supplier in suppliers: risk[supplier_metrics(supplier.id, by_supplier[supplier.id])['risk_level']] += 1
    savings = defaultdict(lambda: {'amount': Decimal('0'), 'comparable_commitments': 0})
    for c in commitments:
        if c.previous_value is not None and c.current_value is not None:
            savings[c.currency]['amount'] += Decimal(c.previous_value) - Decimal(c.current_value)
            savings[c.currency]['comparable_commitments'] += 1
    deadlines = upcoming_deadlines(db)
    recent = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)).all()
    data = {
        'suppliers': {'total': len(suppliers), 'active': sum(s.status == 'active' for s in suppliers), 'by_status': {status: sum(s.status == status for s in suppliers) for status in ['active','inactive','onboarding','suspended']}},
        'interactions': {'total': len(interactions)},
        'commitments': {'total': len(commitments), 'pending': sum(c.status == 'pending' for c in commitments), 'fulfilled': sum(c.status == 'fulfilled' for c in commitments), 'overdue': sum(c.status == 'overdue' for c in commitments), 'breached': sum(c.status == 'breached' for c in commitments), 'verified': sum(c.verified_at is not None for c in commitments), 'active': sum(c.status in {'pending','overdue'} for c in commitments)},
        'risk_distribution': risk,
        'price_savings': [{'currency': currency, **values, 'amount': values['amount']} for currency, values in savings.items()],
        'upcoming_deadlines': [{'id': c.id, 'supplier_id': c.supplier_id, 'title': c.title, 'deadline': c.deadline, 'status': c.status} for c in deadlines],
        'recent_activities': [{'id': a.id, 'action': a.action, 'entity_type': a.entity_type, 'entity_id': a.entity_id, 'created_at': a.created_at, 'user_id': a.user_id} for a in recent],
        'calculation_note': 'All metrics are calculated from persisted records. Savings are separated by currency; unknown risk indicates insufficient terminal commitments.'
    }
    db.commit()
    return {'data': data}

@router.get('/deadlines')
def deadlines(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    refresh_commitment_statuses(db)
    items = upcoming_deadlines(db, days)
    db.commit()
    return {'data': [{'id': c.id, 'supplier_id': c.supplier_id, 'title': c.title, 'deadline': c.deadline, 'status': c.status} for c in items], 'meta': {'days': days}}
