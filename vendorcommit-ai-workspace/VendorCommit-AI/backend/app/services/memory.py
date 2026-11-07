import json
import re
import time
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import MemoryItem


class MemoryError(RuntimeError):
    pass

def get_shared_hindsight_client():
    settings = get_settings()
    try:
        from hindsight_client import Hindsight
    except ImportError as exc:
        raise MemoryError('hindsight-client is not installed') from exc
    return Hindsight(base_url=settings.hindsight_api_url, api_key=settings.hindsight_api_key, timeout=45.0, max_attempts=1)

class HindsightCloudClient:
    """Official Hindsight SDK adapter with a physically isolated bank per supplier."""
    def __init__(self):
        self.client = get_shared_hindsight_client()
        self.bank_prefix = get_settings().hindsight_bank_id

    def bank_for(self, supplier_id: int):
        prefix = re.sub(r'[^a-zA-Z0-9_-]+', '-', self.bank_prefix).strip('-')
        return f'{prefix}-supplier-{supplier_id}'

    def retain(self, supplier_id: int, document_id: str, content: str, metadata: dict):
        provenance = metadata.get('provenance', {})
        self.client.retain(
            bank_id=self.bank_for(supplier_id), content=content, document_id=document_id,
            context='VendorCommit supplier source record',
            metadata={str(k): str(v) for k,v in metadata.items() if k != 'provenance'},
            tags=[f'supplier:{supplier_id}', f"category:{provenance.get('category','source_record')}"],
            retain_async=False,
        )
        return document_id

    def recall(self, supplier_id: int, query: str):
        return self.client.recall(bank_id=self.bank_for(supplier_id), query=query or 'supplier commitments preferences risks negotiations', max_tokens=4096, budget='mid', include_source_facts=True)

class MemoryService:
    def __init__(self):
        self.settings = get_settings()
        self.mode = self.settings.memory_mode
        self._client = None

    @property
    def client(self):
        if self._client is None: self._client = HindsightCloudClient()
        return self._client

    def retain(self, db: Session, supplier_id: int, content: str, provenance: dict):
        item = MemoryItem(supplier_id=supplier_id, content=content, provenance=json.dumps({**provenance, 'source_mode': self.mode, 'ai_generated': False}, default=str), sync_status='local_only' if self.mode == 'LOCAL_MOCK' else 'pending')
        db.add(item); db.flush()
        if self.mode == 'CLOUD': self._sync(item)
        return item

    def _sync(self, item: MemoryItem):
        for attempt in range(self.settings.memory_max_retries + 1):
            try:
                provenance = json.loads(item.provenance or '{}')
                item.external_id = self.client.retain(item.supplier_id, f'vendorcommit-memory-{item.id}', item.content, {'supplier_id':item.supplier_id, 'memory_item_id':item.id, 'title':provenance.get('title','Supplier source record'), 'category':provenance.get('category','source_record'), 'source_interaction_id':provenance.get('source_interaction_id',''), 'provenance':provenance})
                item.sync_status = 'synced'; item.last_error = ''
                return
            except Exception as exc:
                item.retry_count = attempt + 1; item.sync_status = 'failed'; item.last_error = str(exc)[:1000]
                if attempt < self.settings.memory_max_retries: time.sleep(self.settings.memory_retry_backoff_seconds * (2 ** attempt))

    def retry(self, item: MemoryItem):
        if self.mode != 'CLOUD': raise MemoryError('Local mock memories do not require cloud synchronization')
        self._sync(item)
        return item

    def _local_recall(self, db: Session, supplier_id: int, query: str):
        statement = select(MemoryItem).where(MemoryItem.supplier_id == supplier_id)
        for term in [term for term in query.lower().split() if term]: statement = statement.where(MemoryItem.content.ilike(f'%{term}%'))
        return db.scalars(statement.order_by(MemoryItem.created_at.desc())).all()

    @staticmethod
    def _cloud_results(response, supplier_id: int):
        normalized = []
        for result in getattr(response, 'results', []):
            get = lambda name, default=None: getattr(result, name, default)
            metadata = get('metadata', {}) or {}
            mentioned = get('mentioned_at') or get('created_at')
            normalized.append({'id':str(get('id','cloud-memory')), 'supplier_id':supplier_id, 'content':get('text',''), 'title':metadata.get('title',f"Hindsight {get('type','memory')} memory"), 'category':metadata.get('category','source_record'), 'source_interaction_id':metadata.get('source_interaction_id') or None, 'provenance':json.dumps({'hindsight_fact_type':get('type'), 'hindsight_id':str(get('id','')), 'context':get('context'), 'metadata':metadata, 'source_mode':'CLOUD'}, default=str), 'sync_status':'cloud', 'retry_count':0, 'last_error':'', 'external_id':str(get('id','')), 'created_at':mentioned, 'learned_at':mentioned, 'hindsight_fact_type':get('type')})
        return normalized

    def recall(self, db: Session, supplier_id: int, query: str):
        if self.mode == 'CLOUD':
            try:
                response = self.client.recall(supplier_id, query or 'supplier commitments preferences risks negotiations')
                return {'items':self._cloud_results(response,supplier_id), 'mode':self.mode, 'source':'hindsight_cloud', 'ai_generated':False, 'cloud_retrieved':True, 'warning':None}
            except Exception as exc:
                items = self._local_recall(db,supplier_id,query)
                return {'items':items, 'mode':self.mode, 'source':'local_database_fallback', 'ai_generated':False, 'cloud_retrieved':False, 'warning':f'Hindsight Cloud recall unavailable; showing local source records. {str(exc)[:200]}'}
        return {'items':self._local_recall(db,supplier_id,query), 'mode':self.mode, 'source':'local_database', 'ai_generated':False, 'cloud_retrieved':False, 'warning':None}

    def health(self, supplier_id: int = 1):
        if self.mode != 'CLOUD': return {'mode':self.mode,'connected':False,'status':'local_mock','detail':'Local deterministic retrieval; no cloud connection attempted.'}
        try:
            self.client.recall(supplier_id,'health check')
            return {'mode':self.mode,'connected':True,'status':'connected','detail':'Official Hindsight SDK recall succeeded.','supplier_bank':self.client.bank_for(supplier_id)}
        except Exception as exc:
            return {'mode':self.mode,'connected':False,'status':'unavailable','detail':str(exc)[:300]}

    def status(self, db: Session):
        items = db.scalars(select(MemoryItem)).all()
        return {'mode':self.mode,'local_only':sum(i.sync_status=='local_only' for i in items),'pending':sum(i.sync_status=='pending' for i in items),'synced':sum(i.sync_status=='synced' for i in items),'failed':sum(i.sync_status=='failed' for i in items),'ai_generated':False}
