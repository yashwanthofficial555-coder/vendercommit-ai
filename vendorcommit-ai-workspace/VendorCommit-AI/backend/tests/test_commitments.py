from datetime import datetime, timedelta, timezone


def price_payload(supplier_id, **overrides):
    payload = {'supplier_id':supplier_id,'commitment_type':'price','title':'Aluminum unit pricing','previous_value':120,'current_value':100,'currency':'USD','previous_promise':'USD 120','updated_promise':'USD 100'}
    payload.update(overrides); return payload


def test_price_calculations_and_persistence(client, supplier, admin_headers):
    response = client.post('/api/v1/commitments', headers=admin_headers, json=price_payload(supplier['id']))
    assert response.status_code == 201, response.text
    data = response.json()['data']
    assert float(data['savings']) == 20
    assert data['savings_percentage'] == 16.67
    persisted = client.get(f"/api/v1/commitments/{data['id']}", headers=admin_headers).json()['data']
    assert persisted['title'] == 'Aluminum unit pricing'
    assert persisted['verified_at'] is None


def test_independent_verification_workflow(client, supplier, admin_headers, buyer_headers):
    created = client.post('/api/v1/commitments', headers=admin_headers, json=price_payload(supplier['id'])).json()['data']
    own = client.post(f"/api/v1/commitments/{created['id']}/verify", headers=admin_headers, json={'note':'Verified source document'})
    assert own.status_code == 403
    independent = client.post(f"/api/v1/commitments/{created['id']}/verify", headers=buyer_headers, json={'note':'Verified source document'})
    assert independent.status_code == 200
    assert independent.json()['data']['verified_by_id'] != independent.json()['data']['created_by_id']
    updated = client.patch(f"/api/v1/commitments/{created['id']}", headers=admin_headers, json={'current_value':99})
    assert updated.json()['data']['verified_at'] is None


def test_delivery_overdue_and_upcoming_detection(client, supplier, admin_headers):
    base = {'supplier_id':supplier['id'],'commitment_type':'delivery','title':'Delivery commitment'}
    past = client.post('/api/v1/commitments', headers=admin_headers, json={**base,'deadline':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()})
    assert past.status_code == 201
    future = client.post('/api/v1/commitments', headers=admin_headers, json={**base,'title':'Upcoming delivery','deadline':(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()})
    listing = client.get('/api/v1/commitments', headers=admin_headers, params={'status':'overdue'})
    assert listing.json()['meta']['total'] == 1
    deadlines = client.get('/api/v1/dashboard/deadlines', headers=admin_headers, params={'days':30}).json()['data']
    assert len(deadlines) == 1 and deadlines[0]['title'] == 'Upcoming delivery'


def test_quantity_quality_sla_and_breach(client, supplier, admin_headers):
    quantity = client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'quantity','title':'Order quantity','previous_quantity':100,'current_quantity':150,'unit':'kg'})
    assert quantity.status_code == 201
    quality = client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'quality','title':'Quality standard','quality_terms':'ISO 9001'})
    assert quality.status_code == 201
    sla = client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'sla','title':'Response SLA','sla_target':95,'sla_actual':90,'status':'breached'})
    assert sla.json()['data']['is_breached'] is True


def test_commitment_validation_and_filters(client, supplier, admin_headers):
    invalid = client.post('/api/v1/commitments', headers=admin_headers, json={'supplier_id':supplier['id'],'commitment_type':'price','title':'Missing price'})
    assert invalid.status_code == 422
    client.post('/api/v1/commitments', headers=admin_headers, json=price_payload(supplier['id']))
    response = client.get('/api/v1/commitments', headers=admin_headers, params={'commitment_type':'price','supplier_id':supplier['id']})
    assert response.json()['meta']['total'] == 1
    assert client.delete('/api/v1/commitments/9999', headers=admin_headers).status_code == 404
