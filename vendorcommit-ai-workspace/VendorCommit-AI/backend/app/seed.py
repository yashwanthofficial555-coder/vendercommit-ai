from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Commitment, Interaction, MemoryItem, Supplier, User
from .security import hash_password


def seed_demo(db: Session):
    """Opt-in demo fixtures. Never runs automatically unless SEED_DEMO=true."""
    if db.scalar(select(User).limit(1)): return
    admin = User(email='admin@example.com', full_name='Demo Admin', password_hash=hash_password('VendorCommit2026!'), role='admin')
    reviewer = User(email='reviewer@example.com', full_name='Demo Reviewer', password_hash=hash_password('VendorCommit2026!'), role='procurement')
    viewer = User(email='viewer@example.com', full_name='Demo Viewer', password_hash=hash_password('VendorCommit2026!'), role='viewer')
    db.add_all([admin, reviewer, viewer]); db.flush()
    supplier = Supplier(name='Demo Supplier', normalized_name='demosupplier', category='Raw Materials', contact_name='Demo Contact', email='supplier@example.com', location='Demo Location', status='active')
    db.add(supplier); db.flush()
    db.add_all([
        Commitment(supplier_id=supplier.id, created_by_id=admin.id, commitment_type='price', title='Demo price commitment', previous_value=110, current_value=100, currency='USD', previous_promise='USD 110 per unit', updated_promise='USD 100 per unit'),
        Commitment(supplier_id=supplier.id, created_by_id=admin.id, commitment_type='delivery', title='Demo delivery commitment', deadline=datetime.now(timezone.utc)+timedelta(days=14)),
    ])
    db.add(Interaction(supplier_id=supplier.id, author_id=admin.id, interaction_type='note', subject='Demo interaction', content='This is optional seeded demonstration data, not a real supplier record.'))
    db.commit()


def seed_hackathon_story(db: Session):
    """Idempotent, explicitly fictional demo history used to demonstrate memory advantage."""
    if db.scalar(select(Supplier).where(Supplier.normalized_name == 'northstarindustrial')):
        return
    admin = db.scalar(select(User).where(User.role == 'admin').limit(1))
    if not admin: return
    now = datetime.now(timezone.utc)
    northstar = Supplier(name='Northstar Industrial', normalized_name='northstarindustrial', category='Raw Materials', contact_name='James Wilson', email='james@northstar.example.com', location='Chicago, IL', status='active')
    vertex = Supplier(name='Vertex Components', normalized_name='vertexcomponents', category='Components', contact_name='Sarah Miller', email='sarah@vertex.example.com', location='Boston, MA', status='active')
    meridian = Supplier(name='Meridian Logistics', normalized_name='meridianlogistics', category='Logistics', contact_name='Robert Hayes', email='robert@meridian.example.com', location='Seattle, WA', status='active')
    db.add_all([northstar, vertex, meridian]); db.flush()
    events = [
        (northstar, 'meeting', 'September aluminum negotiation', 'James accepted a 7% unit-price reduction when the quarterly aluminum order was consolidated above 10,000 units.', 62),
        (northstar, 'email', 'Consolidated order preference', 'Northstar prefers one consolidated quarterly forecast and can hold the negotiated rate for 30 days when delivery windows are confirmed upfront.', 48),
        (northstar, 'negotiation', 'October pricing review', 'The team used the September volume precedent to negotiate aluminum sheets from USD 120 to USD 110 per unit for the next consolidated order.', 27),
        (vertex, 'delivery', 'August sensor delay', 'Sensor modules arrived six days late because of a semiconductor shortage.', 80),
        (vertex, 'call', 'September delay follow-up', 'Vertex reported the same semiconductor constraint and requested a two-week buffer for sensor-module orders.', 55),
        (meridian, 'email', 'Freight schedule preference', 'Robert prefers consolidated weekly freight schedules and confirmed a 6% reduction for recurring west-coast routes.', 21),
    ]
    interaction_ids = {}
    for supplier, kind, subject, content, days in events:
        item = Interaction(supplier_id=supplier.id, author_id=admin.id, interaction_type=kind, subject=subject, content=content, occurred_at=now-timedelta(days=days))
        db.add(item); db.flush(); interaction_ids[subject] = item.id
    memories = [
        (northstar, 'Volume discount precedent', 'negotiation', 'Northstar accepted a 7% reduction for consolidated aluminum orders above 10,000 units.', 'September aluminum negotiation'),
        (northstar, 'Forecast and rate-hold preference', 'preference', 'One consolidated quarterly forecast is preferred; a 30-day rate hold is available when delivery windows are confirmed upfront.', 'Consolidated order preference'),
        (northstar, 'Observed negotiated price', 'pricing', 'The latest recorded negotiation moved aluminum sheets from USD 120 to USD 110 per unit.', 'October pricing review'),
        (vertex, 'Recurring sensor supply constraint', 'risk', 'Two recorded interactions cite semiconductor shortages; Vertex requested a two-week planning buffer.', 'September delay follow-up'),
        (meridian, 'Recurring route discount', 'pricing', 'Recurring west-coast routes received a recorded 6% freight reduction.', 'Freight schedule preference'),
    ]
    for supplier, title, category, content, source in memories:
        db.add(MemoryItem(supplier_id=supplier.id, content=content, provenance=json.dumps({'title':title,'category':category,'source_interaction_id':interaction_ids[source],'source_mode':'LOCAL_MOCK','ai_generated':False,'demo_data':True}), sync_status='local_only'))
    db.add_all([
        Commitment(supplier_id=northstar.id, created_by_id=admin.id, commitment_type='price', title='Consolidated aluminum sheets', previous_value=120, current_value=110, currency='USD', previous_promise='USD 120 per unit', updated_promise='USD 110 per unit for orders above 10,000 units', deadline=now+timedelta(days=20)),
        Commitment(supplier_id=northstar.id, created_by_id=admin.id, commitment_type='delivery', title='November aluminum delivery', deadline=now+timedelta(days=12), previous_promise='Four weekly shipments', updated_promise='Two consolidated shipments'),
        Commitment(supplier_id=northstar.id, created_by_id=admin.id, commitment_type='quantity', title='September consolidated order', previous_quantity=9000, current_quantity=12000, unit='units', status='fulfilled', fulfilled_at=now-timedelta(days=45)),
        Commitment(supplier_id=vertex.id, created_by_id=admin.id, commitment_type='delivery', title='Precision sensor modules', deadline=now+timedelta(days=8), previous_promise='Standard 30-day lead time', updated_promise='Add two-week supply buffer'),
        Commitment(supplier_id=vertex.id, created_by_id=admin.id, commitment_type='delivery', title='August sensor shipment', deadline=now-timedelta(days=80), status='breached', previous_promise='On-time delivery', updated_promise='Delivered six days late'),
        Commitment(supplier_id=meridian.id, created_by_id=admin.id, commitment_type='price', title='Recurring west-coast freight', previous_value=50000, current_value=47000, currency='USD', status='fulfilled', fulfilled_at=now-timedelta(days=10)),
    ])
    db.commit()
