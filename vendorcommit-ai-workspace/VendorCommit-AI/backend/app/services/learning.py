from sqlalchemy.orm import Session
from ..models import Interaction, MemoryItem
from .memory import MemoryService


def classify_source(interaction: Interaction):
    """Transparent keyword rules classify source text; no facts are generated or inferred."""
    text = f'{interaction.subject} {interaction.content}'.lower()
    if any(term in text for term in ('delay', 'late', 'shortage', 'disruption', 'backorder')):
        return 'risk'
    if any(term in text for term in ('discount', 'price', 'pricing', 'rate', 'concession', 'negotiat')):
        return 'negotiation'
    if any(term in text for term in ('prefer', 'preference', 'would like', 'required format')):
        return 'preference'
    if interaction.interaction_type == 'delivery':
        return 'delivery'
    return 'source_record'


def learn_from_interaction(db: Session, interaction: Interaction) -> MemoryItem:
    """Retain the original interaction verbatim with explicit, inspectable provenance."""
    return MemoryService().retain(
        db,
        interaction.supplier_id,
        interaction.content,
        {
            'title': interaction.subject,
            'category': classify_source(interaction),
            'source_interaction_id': interaction.id,
            'retention_trigger': 'interaction_created',
            'extraction_method': 'verbatim_source_retention',
            'ai_generated': False,
        },
    )
