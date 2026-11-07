from app.models import Supplier


def test_authentication_and_me(client, admin_headers):
    assert client.get('/api/v1/suppliers').status_code == 401
    assert client.post('/api/v1/auth/login', json={'email':'admin@example.com','password':'wrong-password'}).status_code == 401
    me = client.get('/api/v1/auth/me', headers=admin_headers)
    assert me.status_code == 200
    assert me.json()['data']['role'] == 'admin'
    assert 'password_hash' not in me.json()['data']


def test_role_based_access_control(client, supplier, viewer_headers, buyer_headers, admin_headers):
    assert client.post('/api/v1/suppliers', headers=viewer_headers, json={'name':'Forbidden Co'}).status_code == 403
    assert client.delete(f"/api/v1/suppliers/{supplier['id']}", headers=buyer_headers).status_code == 403
    assert client.delete(f"/api/v1/suppliers/{supplier['id']}", headers=admin_headers).status_code == 204


def test_supplier_crud_duplicate_search_sort_and_persistence(client, db, supplier, admin_headers):
    duplicate = client.post('/api/v1/suppliers', headers=admin_headers, json={'name':'North-Star Industrial!'})
    assert duplicate.status_code == 409
    duplicate_email = client.post('/api/v1/suppliers', headers=admin_headers, json={'name':'Different Name','email':'JAMES@example.com'})
    assert duplicate_email.status_code == 409
    response = client.patch(f"/api/v1/suppliers/{supplier['id']}", headers=admin_headers, json={'location':'Chicago, IL','status':'onboarding'})
    assert response.status_code == 200
    assert response.json()['data']['location'] == 'Chicago, IL'
    assert response.json()['data']['risk_level'] == 'unknown'
    db.expire_all()
    assert db.get(Supplier, supplier['id']).location == 'Chicago, IL'
    assert client.get('/api/v1/suppliers', headers=admin_headers, params={'search':'Northstar','status':'onboarding'}).json()['meta']['total'] == 1
    injection = client.get('/api/v1/suppliers', headers=admin_headers, params={'search':"%' OR 1=1 --"})
    assert injection.status_code == 200
    assert injection.json()['meta']['total'] == 0


def test_supplier_pagination_and_status(client, admin_headers):
    for index in range(3):
        client.post('/api/v1/suppliers', headers=admin_headers, json={'name':f'Supplier {index}','category':'Services'})
    response = client.get('/api/v1/suppliers', headers=admin_headers, params={'page':2,'page_size':2,'sort':'name','order':'desc'})
    assert response.status_code == 200
    assert response.json()['meta'] == {'total':3,'page':2,'page_size':2,'pages':2}
    assert len(response.json()['data']) == 1
    supplier_id = response.json()['data'][0]['id']
    changed = client.patch(f'/api/v1/suppliers/{supplier_id}/status', headers=admin_headers, json={'status':'inactive'})
    assert changed.json()['data']['status'] == 'inactive'


def test_supplier_validation(client, admin_headers):
    assert client.post('/api/v1/suppliers', headers=admin_headers, json={'name':'x','email':'not-an-email'}).status_code == 422
    assert client.get('/api/v1/suppliers/9999', headers=admin_headers).status_code == 404
