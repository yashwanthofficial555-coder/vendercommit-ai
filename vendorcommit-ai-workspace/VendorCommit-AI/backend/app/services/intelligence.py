from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Commitment, PerformanceHistory, Supplier


def aware(value: datetime | None):
    if value is None: return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def calculate_savings(commitment: Commitment):
    if commitment.previous_value is None or commitment.current_value is None:
        return None, None
    savings = Decimal(commitment.previous_value) - Decimal(commitment.current_value)
    percentage = float(savings / Decimal(commitment.previous_value) * 100) if commitment.previous_value else None
    return savings, round(percentage, 2) if percentage is not None else None


def refresh_commitment_statuses(db: Session):
    now = datetime.now(timezone.utc)
    changed = False
    for commitment in db.scalars(select(Commitment).where(Commitment.status == 'pending')).all():
        deadline = aware(commitment.deadline)
        if deadline and deadline < now:
            commitment.status = 'overdue'
            changed = True
    if changed: db.flush()


def supplier_metrics(supplier_id: int, commitments: list[Commitment]):
    terminal = [c for c in commitments if c.status in {'fulfilled', 'breached'}]
    if not terminal:
        return {'reliability_score': None, 'delivery_score': None, 'risk_level': 'unknown', 'fulfilled_count': 0, 'breached_count': 0, 'active_commitments': sum(c.status in {'pending','overdue'} for c in commitments)}
    fulfilled = [c for c in terminal if c.status == 'fulfilled']
    breached = [c for c in terminal if c.status == 'breached']
    reliability = round(len(fulfilled) / len(terminal) * 100, 2)
    delivery_commitments = [c for c in terminal if c.deadline is not None and c.fulfilled_at is not None]
    delivery = round(sum(aware(c.fulfilled_at) <= aware(c.deadline) for c in delivery_commitments) / len(delivery_commitments) * 100, 2) if delivery_commitments else None
    overdue_active = sum(c.status == 'overdue' for c in commitments)
    risk = 'high' if reliability < 60 or overdue_active >= 3 else 'medium' if reliability < 85 or overdue_active else 'low'
    return {'reliability_score': reliability, 'delivery_score': delivery, 'risk_level': risk, 'fulfilled_count': len(fulfilled), 'breached_count': len(breached), 'active_commitments': sum(c.status in {'pending','overdue'} for c in commitments)}


def serialize_commitment(c: Commitment):
    savings, percentage = calculate_savings(c)
    data = {column.name: getattr(c, column.name) for column in c.__table__.columns}
    data.update(savings=savings, savings_percentage=percentage, is_breached=c.status == 'breached' or (c.sla_target is not None and c.sla_actual is not None and c.sla_actual > c.sla_target))
    return data


def supplier_out(db: Session, supplier: Supplier):
    refresh_commitment_statuses(db)
    commitments = db.scalars(select(Commitment).where(Commitment.supplier_id == supplier.id)).all()
    data = {column.name: getattr(supplier, column.name) for column in supplier.__table__.columns}
    data.update(supplier_metrics(supplier.id, commitments))
    return data


def record_performance(db: Session, supplier_id: int):
    commitments = db.scalars(select(Commitment).where(Commitment.supplier_id == supplier_id)).all()
    metrics = supplier_metrics(supplier_id, commitments)
    if metrics['reliability_score'] is None: return None
    snapshot = PerformanceHistory(supplier_id=supplier_id, **{k:v for k,v in metrics.items() if k in {'reliability_score','delivery_score','risk_level','fulfilled_count','breached_count'}})
    db.add(snapshot)
    return snapshot


def upcoming_deadlines(db: Session, days: int = 30):
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    commitments = db.scalars(select(Commitment).where(Commitment.status == 'pending', Commitment.deadline.is_not(None))).all()
    return sorted([c for c in commitments if now <= aware(c.deadline) <= end], key=lambda c: aware(c.deadline))
