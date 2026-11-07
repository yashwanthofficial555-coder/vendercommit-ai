from types import SimpleNamespace
from datetime import datetime, timezone
from app.services.memory import MemoryService


def test_local_mock_retain_recall_isolation_and_provenance(client, supplier, admin_headers):
    other = client.post('/api/v1/suppliers', headers=admin_headers, json={'name':'Other Supplier'}).json()['data']
    retained = client.post('/api/v1/memory/retain', headers=admin_headers, json={'supplier_id':supplier['id'],'content':'Quarterly price preference for aluminum','provenance':{'interaction_id':123}})
    assert retained.status_code == 201
    assert retained.json()['data']['sync_status'] == 'local_only'
    assert retained.json()['meta']['ai_generated'] is False
    client.post('/api/v1/memory/retain', headers=admin_headers, json={'supplier_id':other['id'],'content':'Unrelated confidential supplier memory'})
    result = client.get(f"/api/v1/memory/recall/{supplier['id']}", headers=admin_headers, params={'query':'aluminum'}).json()['data']
    assert result['source'] == 'local_database'
    assert result['cloud_retrieved'] is False
    assert len(result['items']) == 1
    assert 'aluminum' in result['items'][0]['content']
    assert client.get(f"/api/v1/memory/recall/{supplier['id']}", headers=admin_headers, params={'query':'confidential'}).json()['data']['items'] == []
    status = client.get('/api/v1/memory/status', headers=admin_headers).json()['data']
    assert status == {'mode':'LOCAL_MOCK','local_only':2,'pending':0,'synced':0,'failed':0,'ai_generated':False}
    retry = client.post(f"/api/v1/memory/{retained.json()['data']['id']}/retry", headers=admin_headers)
    assert retry.status_code == 409


def test_historical_commitment_retrieval(client, supplier, admin_headers):
    client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'price','title':'Historic price','previous_value':110,'current_value':100})
    result = client.get(f"/api/v1/memory/history/{supplier['id']}", headers=admin_headers)
    assert result.json()['meta']['source'] == 'operational_database'
    assert len(result.json()['data']) == 1


def test_memory_insights_change_decision_support_with_traceable_evidence(client, supplier, admin_headers):
    interaction = client.post('/api/v1/interactions', headers=admin_headers, json={'supplier_id':supplier['id'],'interaction_type':'negotiation','subject':'Volume negotiation','content':'Supplier accepted 7% off above 10,000 units.'}).json()['data']
    client.post('/api/v1/memory/retain', headers=admin_headers, json={'supplier_id':supplier['id'],'content':'Supplier accepted 7% off above 10,000 units.','provenance':{'title':'Volume precedent','category':'negotiation','source_interaction_id':interaction['id']}})
    insights = client.get(f"/api/v1/memory/insights/{supplier['id']}", headers=admin_headers).json()['data']
    assert insights['memory_count'] == 2
    assert insights['categories'] == {'negotiation':2}
    assert insights['evidence'][0]['source_interaction_id'] == interaction['id']
    comparison = client.get(f"/api/v1/memory/compare/{supplier['id']}", headers=admin_headers, params={'scenario':'price_negotiation'}).json()['data']
    assert comparison['without_memory']['evidence_ids'] == []
    assert comparison['with_memory']['memory_changed_decision_support'] is True
    assert comparison['with_memory']['recalled_evidence'][0]['title'] == 'Volume precedent'
    assert '7%' in comparison['with_memory']['recommendation'][0]


def test_comparison_does_not_invent_relevant_memory(client, supplier, admin_headers):
    comparison = client.get(f"/api/v1/memory/compare/{supplier['id']}", headers=admin_headers).json()['data']
    assert comparison['with_memory']['memory_changed_decision_support'] is False
    assert comparison['with_memory']['recalled_evidence'] == []
    assert 'No scenario-relevant' in comparison['with_memory']['recommendation'][0]


def test_cloud_memory_failures_are_recorded_and_retryable(db, supplier):
    class FailingClient:
        def retain(self, supplier_id, document_id, content, metadata): raise ConnectionError('Cloud unavailable')
    service = MemoryService()
    service.mode = 'CLOUD'
    service.settings = SimpleNamespace(memory_max_retries=2, memory_retry_backoff_seconds=0)
    service._client = FailingClient()
    item = service.retain(db, supplier['id'], 'Test cloud memory', {'test':True})
    db.commit()
    assert item.sync_status == 'failed'
    assert item.retry_count == 3
    assert item.last_error == 'Cloud unavailable'
    assert item.external_id == ''


def test_cloud_recall_uses_supplier_bank_and_reports_provenance(db, supplier):
    class CloudClient:
        def bank_for(self, supplier_id): return f'demo-supplier-{supplier_id}'
        def recall(self, supplier_id, query):
            assert supplier_id == supplier['id']
            return SimpleNamespace(results=[SimpleNamespace(id='fact-123',text='Supplier prefers consolidated orders',type='observation',context='procurement',metadata={'category':'preference','title':'Order preference','source_interaction_id':'42'},mentioned_at=datetime.now(timezone.utc))])
    service = MemoryService(); service.mode = 'CLOUD'; service._client = CloudClient()
    result = service.recall(db,supplier['id'],'order preferences')
    assert result['source'] == 'hindsight_cloud'
    assert result['cloud_retrieved'] is True
    assert result['items'][0]['external_id'] == 'fact-123'
    assert result['items'][0]['category'] == 'preference'
    assert service.health(supplier['id'])['connected'] is True


def test_cloud_recall_failure_is_explicit_and_falls_back_to_local(db, supplier):
    class FailingCloud:
        def recall(self, supplier_id, query): raise ConnectionError('Cloud timeout')
    MemoryService().retain(db,supplier['id'],'Local source fact',{'category':'source_record'})
    service = MemoryService(); service.mode = 'CLOUD'; service._client = FailingCloud()
    result = service.recall(db,supplier['id'],'Local')
    assert result['source'] == 'local_database_fallback'
    assert result['cloud_retrieved'] is False
    assert 'Cloud timeout' in result['warning']
    assert len(result['items']) == 1
