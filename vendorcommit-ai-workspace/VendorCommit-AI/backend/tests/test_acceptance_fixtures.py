import json
from sqlalchemy import func, select
from app.acceptance_fixtures import seed_acceptance_story
from app.models import Commitment, Interaction, MemoryItem, PerformanceHistory, Supplier


def test_acceptance_fixtures_cover_all_states_and_are_idempotent(db):
    first = seed_acceptance_story(db)
    assert first == {'suppliers': 4, 'commitments': 12, 'interactions': 6, 'memories': 7}
    counts = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Supplier, Commitment, Interaction, MemoryItem, PerformanceHistory))
    seed_acceptance_story(db)
    assert counts == tuple(db.scalar(select(func.count()).select_from(model)) for model in (Supplier, Commitment, Interaction, MemoryItem, PerformanceHistory))

    suppliers = db.scalars(select(Supplier).where(Supplier.name.like('QA %'))).all()
    assert {s.status for s in suppliers} == {'active', 'onboarding', 'suspended', 'inactive'}
    commitments = db.scalars(select(Commitment).where(Commitment.title.like('QA %'))).all()
    assert {c.commitment_type for c in commitments} == {'price', 'delivery', 'quantity', 'quality', 'sla'}
    assert {c.status for c in commitments} == {'pending', 'fulfilled', 'overdue', 'breached'}
    verified = next(c for c in commitments if c.title == 'QA verified packaging price')
    assert verified.created_by_id != verified.verified_by_id
    interactions = db.scalars(select(Interaction).where(Interaction.subject.like('QA %'))).all()
    assert {i.interaction_type for i in interactions} == {'call', 'email', 'meeting', 'delivery', 'note', 'negotiation'}
    memories = db.scalars(select(MemoryItem).where(MemoryItem.content.like('QA-%'))).all()
    assert all(json.loads(memory.provenance)['demo_data'] is True for memory in memories)
    assert all(json.loads(memory.provenance)['ai_generated'] is False for memory in memories)
    failed = next(memory for memory in memories if memory.sync_status == 'failed')
    assert json.loads(failed.provenance)['simulated_failure'] is True
    failed.sync_status = 'synced'
    db.commit()
    seed_acceptance_story(db, simulate_failure=True)
    assert failed.sync_status == 'failed'
    assert failed.retry_count == 3
