import os
os.environ['DATABASE_URL'] = 'sqlite:///./test-vendorcommit.db'
os.environ['SEED_DEMO'] = 'false'
os.environ['AUTH_REQUIRED'] = 'true'
os.environ['MEMORY_MODE'] = 'LOCAL_MOCK'
os.environ['RATE_LIMIT_REQUESTS'] = '10000'
os.environ['JWT_SECRET'] = 'test-secret-that-is-long-enough-for-testing-only'

import pytest
from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User
from app.security import hash_password

@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    users = [
        User(email='admin@example.com', full_name='Admin User', password_hash=hash_password('AdminPassword123!'), role='admin'),
        User(email='buyer@example.com', full_name='Buyer User', password_hash=hash_password('BuyerPassword123!'), role='procurement'),
        User(email='viewer@example.com', full_name='Viewer User', password_hash=hash_password('ViewerPassword123!'), role='viewer'),
    ]
    session.add_all(users); session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def client(db):
    with TestClient(app) as test_client:
        yield test_client

def token(client, email='admin@example.com', password='AdminPassword123!'):
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200, response.text
    return response.json()['data']['access_token']

@pytest.fixture()
def admin_headers(client): return {'Authorization': f'Bearer {token(client)}'}
@pytest.fixture()
def buyer_headers(client): return {'Authorization': f'Bearer {token(client, "buyer@example.com", "BuyerPassword123!")}'}
@pytest.fixture()
def viewer_headers(client): return {'Authorization': f'Bearer {token(client, "viewer@example.com", "ViewerPassword123!")}'}

@pytest.fixture()
def supplier(client, admin_headers):
    response = client.post('/api/v1/suppliers', headers=admin_headers, json={'name':'Northstar Industrial','category':'Materials','contact_name':'James Wilson','email':'james@example.com','status':'active'})
    assert response.status_code == 201, response.text
    return response.json()['data']
