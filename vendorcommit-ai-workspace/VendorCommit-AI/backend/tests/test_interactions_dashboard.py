from app.models import AuditLog


def test_interaction_crud_history_and_audit(client, db, supplier, admin_headers):
    created = client.post('/api/v1/interactions', headers=admin_headers, json={'supplier_id':supplier['id'],'interaction_type':'meeting','subject':'Quarterly review','content':'Discussed pricing and delivery.'})
    assert created.status_code == 201
    item = created.json()['data']
    assert created.json()['meta']['retention_method'] == 'verbatim_source_retention'
    assert created.json()['meta']['ai_generated'] is False
    recalled = client.get(f"/api/v1/memory/recall/{supplier['id']}", headers=admin_headers, params={'query':'pricing'}).json()['data']
    assert len(recalled['items']) == 1
    updated = client.patch(f"/api/v1/interactions/{item['id']}", headers=admin_headers, json={'content':'Updated meeting record.'})
    assert updated.status_code == 200
    history = client.get('/api/v1/interactions', headers=admin_headers, params={'supplier_id':supplier['id'],'interaction_type':'meeting'})
    assert history.json()['meta']['total'] == 1
    assert client.get('/api/v1/audit-logs', headers=admin_headers).status_code == 200
    actions = [log.action for log in db.query(AuditLog).all()]
    assert 'create' in actions and 'update' in actions
    assert client.delete(f"/api/v1/interactions/{item['id']}", headers=admin_headers).status_code == 204


def test_empty_dashboard_has_no_fabricated_metrics(client, admin_headers):
    data = client.get('/api/v1/dashboard/executive', headers=admin_headers).json()['data']
    assert data['suppliers']['total'] == 0
    assert data['commitments']['total'] == 0
    assert data['price_savings'] == []
    assert data['risk_distribution'] == {'low':0,'medium':0,'high':0,'unknown':0}


def test_dashboard_uses_database_calculations(client, supplier, admin_headers, buyer_headers):
    commitment = client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'price','title':'Price record','previous_value':100,'current_value':90,'currency':'USD'}).json()['data']
    client.post(f"/api/v1/commitments/{commitment['id']}/verify", headers=buyer_headers, json={'note':'Confirmed independently'})
    client.post('/api/v1/interactions', headers=admin_headers, json={'supplier_id':supplier['id'],'interaction_type':'email','subject':'Price email','content':'Confirmed current price.'})
    data = client.get('/api/v1/dashboard/executive', headers=admin_headers).json()['data']
    assert data['suppliers'] == {'total':1,'active':1,'by_status':{'active':1,'inactive':0,'onboarding':0,'suspended':0}}
    assert data['commitments']['verified'] == 1
    assert data['interactions']['total'] == 1
    assert float(data['price_savings'][0]['amount']) == 10
    assert data['risk_distribution']['unknown'] == 1


def test_performance_snapshot_requires_terminal_data(client, supplier, admin_headers):
    assert client.post(f"/api/v1/suppliers/{supplier['id']}/performance/snapshot", headers=admin_headers).status_code == 409
    created = client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'price','title':'Completed price agreement','current_value':100,'status':'fulfilled'})
    assert created.status_code == 201
    snapshot = client.post(f"/api/v1/suppliers/{supplier['id']}/performance/snapshot", headers=admin_headers)
    assert snapshot.status_code == 201
    assert snapshot.json()['data']['reliability_score'] == 100
    history = client.get(f"/api/v1/suppliers/{supplier['id']}/performance", headers=admin_headers)
    assert len(history.json()['data']) == 1
