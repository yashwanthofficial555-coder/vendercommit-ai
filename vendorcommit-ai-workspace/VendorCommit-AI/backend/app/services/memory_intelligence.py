import json
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Commitment, Interaction, MemoryItem


def provenance(item: MemoryItem):
    try: return json.loads(item.provenance or '{}')
    except (TypeError, json.JSONDecodeError): return {}


def supplier_memory_insights(db: Session, supplier_id: int):
    items = db.scalars(select(MemoryItem).where(MemoryItem.supplier_id == supplier_id).order_by(MemoryItem.created_at.asc())).all()
    interactions = db.scalars(select(Interaction).where(Interaction.supplier_id == supplier_id).order_by(Interaction.occurred_at.asc())).all()
    commitments = db.scalars(select(Commitment).where(Commitment.supplier_id == supplier_id).order_by(Commitment.created_at.asc())).all()
    categories = Counter(provenance(item).get('category', 'source_record') for item in items)
    evidence = []
    for item in reversed(items):
        meta = provenance(item)
        evidence.append({'id': item.id, 'title': meta.get('title', 'Retained source record'), 'category': meta.get('category', 'source_record'), 'content': item.content, 'source_interaction_id': meta.get('source_interaction_id'), 'learned_at': item.created_at, 'provenance': meta, 'sync_status': item.sync_status})
    return {
        'memory_count': len(items), 'interaction_count': len(interactions), 'commitment_count': len(commitments),
        'categories': dict(categories), 'evidence': evidence,
        'timeline': [{'id': i.id, 'type': i.interaction_type, 'subject': i.subject, 'content': i.content, 'occurred_at': i.occurred_at} for i in interactions],
        'method': 'Deterministic retrieval over explicitly retained source records; no AI-generated facts.'
    }


def compare_memory_decision(db: Session, supplier_id: int, scenario: str, recalled_evidence: list | None = None, retrieval: dict | None = None):
    insight = supplier_memory_insights(db, supplier_id)
    current = db.scalars(select(Commitment).where(Commitment.supplier_id == supplier_id).order_by(Commitment.created_at.desc())).all()
    evidence = insight['evidence'] if recalled_evidence is None else recalled_evidence
    baseline = {
        'context_used': ['Current operational commitment records only'],
        'recommendation': 'Review the latest supplier terms and request updated confirmation.',
        'missing_context': ['Prior negotiation precedents', 'Recurring relationship patterns', 'Previously recorded supplier preferences'],
        'evidence_ids': []
    }
    actions = []
    used = []
    for item in evidence:
        category = item['category']
        if scenario == 'price_negotiation' and category in {'negotiation', 'pricing', 'preference'}:
            actions.append(f"Use this recorded precedent in the negotiation: {item['content']}")
            used.append(item)
        elif scenario == 'delivery_planning' and category in {'risk', 'delivery', 'preference'}:
            actions.append(f"Account for this retained delivery context: {item['content']}")
            used.append(item)
    if not actions:
        actions = ['No scenario-relevant retained evidence was found. Confirm requirements directly with the supplier.']
    enriched = {
        'context_used': ['Current operational commitment records', f"{len(used)} supplier-specific retained evidence records"],
        'recommendation': actions,
        'recalled_evidence': used,
        'current_commitment_count': len(current),
        'memory_changed_decision_support': bool(used),
        'method': 'Rule-based decision support grounded only in the evidence returned below.'
    }
    return {'scenario': scenario, 'without_memory': baseline, 'with_memory': enriched, 'retrieval': retrieval or {'source':'local_database','cloud_retrieved':False,'warning':None}}
