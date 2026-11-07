"""Fictional, idempotent acceptance fixtures. Never deletes or rewrites user data."""
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Commitment, Interaction, MemoryItem, PerformanceHistory, Supplier, User
from .services.intelligence import record_performance, refresh_commitment_statuses

PREFIX = 'QA '
DEMO_NOTE = 'Fictional acceptance-test fixture; not a real supplier, transaction, or verified event.'


def _get_or_create_supplier(db: Session, name: str, **values):
    normalized = ''.join(character for character in name.lower() if character.isalnum())
    supplier = db.scalar(select(Supplier).where(Supplier.normalized_name == normalized))
    if supplier:
        return supplier
    supplier = Supplier(name=name, normalized_name=normalized, **values)
    db.add(supplier)
    db.flush()
    return supplier


def seed_acceptance_story(db: Session, simulate_failure: bool = False):
    """Seed all UI states independently so partially populated databases are safe."""
    admin = db.scalar(select(User).where(User.role == 'admin').limit(1))
    reviewer = db.scalar(select(User).where(User.role == 'procurement').limit(1))
    if not admin or not reviewer:
        return {'suppliers': 0, 'commitments': 0, 'interactions': 0, 'memories': 0}

    now = datetime.now(timezone.utc)
    suppliers = {
        'atlas': _get_or_create_supplier(db, 'QA Atlas Packaging', category='Packaging', contact_name='Avery Stone', email='qa.atlas@example.com', location='Austin, TX', status='active'),
        'beacon': _get_or_create_supplier(db, 'QA Beacon Electronics', category='Electronics', contact_name='Blake Chen', email='qa.beacon@example.com', location='Portland, OR', status='onboarding'),
        'cobalt': _get_or_create_supplier(db, 'QA Cobalt Textiles', category='Textiles', contact_name='Casey Rao', email='qa.cobalt@example.com', location='Raleigh, NC', status='suspended'),
        'delta': _get_or_create_supplier(db, 'QA Delta Freight', category='Logistics', contact_name='Devon Lee', email='qa.delta@example.com', location='Denver, CO', status='inactive'),
    }

    interactions = [
        ('atlas', 'meeting', 'QA packaging negotiation', 'QA-ATLAS-VOLUME: Atlas accepted a fictional 8% discount for recurring pallet orders above 5,000 units.', 'Volume discount', 'negotiation'),
        ('atlas', 'note', 'QA packaging storage preference', 'QA-ATLAS-STORAGE: Atlas prefers recyclable cartons and delivery appointments booked 48 hours ahead.', 'Packaging preference', 'preference'),
        ('beacon', 'call', 'QA component risk call', 'QA-BEACON-LEADTIME: Beacon requested a fictional 21-day lead-time buffer for power controllers.', 'Lead-time risk', 'risk'),
        ('cobalt', 'delivery', 'QA textile delivery review', 'QA-COBALT-QUALITY: Cobalt recorded a fictional dye-lot variance and now requires pre-shipment samples.', 'Quality precedent', 'risk'),
        ('delta', 'email', 'QA freight scheduling email', 'QA-DELTA-ROUTES: Delta prefers fictional Tuesday pickups for consolidated regional routes.', 'Route preference', 'preference'),
        ('delta', 'negotiation', 'QA fuel surcharge negotiation', 'QA-DELTA-SURCHARGE: Delta agreed to a fictional fuel-surcharge cap of 4% on recurring routes.', 'Surcharge precedent', 'pricing'),
    ]
    interaction_ids = {}
    for key, kind, subject, content, title, category in interactions:
        supplier = suppliers[key]
        interaction = db.scalar(select(Interaction).where(Interaction.supplier_id == supplier.id, Interaction.subject == subject))
        if not interaction:
            interaction = Interaction(supplier_id=supplier.id, author_id=admin.id, interaction_type=kind, subject=subject, content=f'{content} {DEMO_NOTE}', occurred_at=now - timedelta(days=10))
            db.add(interaction)
            db.flush()
        interaction_ids[subject] = interaction.id
        memory = db.scalar(select(MemoryItem).where(MemoryItem.supplier_id == supplier.id, MemoryItem.content == content))
        if not memory:
            provenance = {'title': title, 'category': category, 'source_interaction_id': interaction.id, 'source_mode': 'LOCAL_MOCK', 'ai_generated': False, 'demo_data': True}
            db.add(MemoryItem(supplier_id=supplier.id, content=content, provenance=json.dumps(provenance), sync_status='local_only'))

    failure_content = 'QA-RETRY-RECOVERY: This fictional packaging record is provided to test failed-memory retry behavior.'
    failed = db.scalar(select(MemoryItem).where(MemoryItem.supplier_id == suppliers['atlas'].id, MemoryItem.content == failure_content))
    if not failed:
        provenance = {'title': 'Simulated retry recovery', 'category': 'negotiation', 'source_interaction_id': interaction_ids['QA packaging negotiation'], 'source_mode': 'LOCAL_MOCK', 'ai_generated': False, 'demo_data': True, 'simulated_failure': True}
        db.add(MemoryItem(supplier_id=suppliers['atlas'].id, content=failure_content, provenance=json.dumps(provenance), sync_status='failed', retry_count=3, last_error='Simulated demo failure: use Retry to send this source record to Hindsight.'))
    elif simulate_failure and failed:
        # Explicit opt-in reset of this QA-only fixture; never touches real memory records.
        failed.sync_status = 'failed'
        failed.retry_count = 3
        failed.last_error = 'Simulated demo failure: use Retry to send this source record to Hindsight.'

    commitments = [
        ('atlas', dict(commitment_type='price', title='QA verified packaging price', previous_value=250, current_value=225, currency='USD', previous_promise='USD 250 per pallet', updated_promise='USD 225 per pallet', status='fulfilled', fulfilled_at=now-timedelta(days=3), created_by_id=reviewer.id, verified_by_id=admin.id, verified_at=now-timedelta(days=2), verification_note='Fictional independent verification example.')),
        ('atlas', dict(commitment_type='price', title='QA independent verification target', previous_value=100, current_value=92, currency='USD', status='pending', created_by_id=reviewer.id)),
        ('atlas', dict(commitment_type='delivery', title='QA upcoming packaging delivery', deadline=now+timedelta(days=9), previous_promise='Four weekly drops', updated_promise='Two consolidated deliveries', status='pending', created_by_id=admin.id)),
        ('atlas', dict(commitment_type='quantity', title='QA recyclable carton quantity', previous_quantity=5000, current_quantity=6000, unit='cartons', status='fulfilled', fulfilled_at=now-timedelta(days=5), created_by_id=admin.id)),
        ('beacon', dict(commitment_type='sla', title='QA controller response SLA', sla_target=95, sla_actual=88, status='breached', deadline=now-timedelta(days=7), created_by_id=admin.id)),
        ('beacon', dict(commitment_type='delivery', title='QA overdue controller delivery', deadline=now-timedelta(days=2), previous_promise='Standard lead time', updated_promise='Expedite overdue shipment', status='pending', created_by_id=admin.id)),
        ('beacon', dict(commitment_type='price', title='QA component cost increase', previous_value=80, current_value=84, currency='USD', status='fulfilled', fulfilled_at=now-timedelta(days=4), created_by_id=admin.id)),
        ('cobalt', dict(commitment_type='quality', title='QA textile dye-lot quality', quality_terms='Pre-shipment sample required; fictional maximum variance 1%.', status='breached', created_by_id=admin.id)),
        ('cobalt', dict(commitment_type='delivery', title='QA fulfilled textile delivery', deadline=now-timedelta(days=6), status='fulfilled', fulfilled_at=now-timedelta(days=7), created_by_id=admin.id)),
        ('cobalt', dict(commitment_type='quantity', title='QA pending textile quantity', previous_quantity=1000, current_quantity=1200, unit='rolls', status='pending', created_by_id=admin.id)),
        ('delta', dict(commitment_type='price', title='QA pending freight rate', previous_value=10000, current_value=9000, currency='USD', status='pending', created_by_id=admin.id)),
        ('delta', dict(commitment_type='sla', title='QA fulfilled freight SLA', sla_target=98, sla_actual=97, status='fulfilled', fulfilled_at=now-timedelta(days=8), created_by_id=admin.id)),
    ]
    for key, values in commitments:
        supplier = suppliers[key]
        commitment = db.scalar(select(Commitment).where(Commitment.supplier_id == supplier.id, Commitment.title == values['title']))
        if not commitment:
            db.add(Commitment(supplier_id=supplier.id, description=DEMO_NOTE, **values))

    db.flush()
    refresh_commitment_statuses(db)
    for supplier in suppliers.values():
        has_history = db.scalar(select(PerformanceHistory).where(PerformanceHistory.supplier_id == supplier.id).limit(1))
        if not has_history:
            record_performance(db, supplier.id)
    db.commit()
    return {'suppliers': len(suppliers), 'commitments': len(commitments), 'interactions': len(interactions), 'memories': len(interactions) + 1}
