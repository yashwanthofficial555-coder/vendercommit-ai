"""Live API acceptance checks for the fictional QA fixtures.

Run from backend/: python scripts/verify_live.py
Only QA-prefixed fixtures and temporary QA-LIVE-CRUD records are touched.
Authentication is optional; set DEMO_ADMIN_EMAIL/PASSWORD when AUTH_REQUIRED=true.
"""
from datetime import datetime, timedelta, timezone
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.getenv('VENDORCOMMIT_API_URL', 'http://127.0.0.1:8000').rstrip('/') + '/api/v1'
TOKEN = None
PASSED = []


def request(method, path, payload=None, expected=200, token=None):
    headers = {}
    active_token = token if token is not None else TOKEN
    if active_token:
        headers['Authorization'] = f'Bearer {active_token}'
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    try:
        with urlopen(Request(BASE + path, data=data, headers=headers, method=method), timeout=120) as response:
            status = response.status
            body = response.read()
    except HTTPError as error:
        status = error.code
        body = error.read()
    assert status == expected, f'{method} {path}: expected {expected}, got {status}: {body.decode()}'
    return json.loads(body) if body else None


def check(name, condition=True):
    assert condition, name
    PASSED.append(name)
    print(f'PASS  {name}')


def login_if_needed():
    global TOKEN
    try:
        request('GET', '/suppliers?page_size=1')
        return 'open local demo'
    except AssertionError:
        email = os.getenv('DEMO_ADMIN_EMAIL', 'admin@example.com')
        password = os.getenv('DEMO_ADMIN_PASSWORD', 'VendorCommit2026!')
        result = request('POST', '/auth/login', {'email': email, 'password': password})
        TOKEN = result['data']['access_token']
        return 'authenticated API'


def list_all(path):
    result = request('GET', path + ('&' if '?' in path else '?') + 'page_size=100')
    return result['data']


def main():
    print('Testing', BASE)
    print('Access mode:', login_if_needed())
    suppliers = list_all('/suppliers')
    qa = {s['name']: s for s in suppliers if s['name'].startswith('QA ') and not s['name'].startswith('QA-LIVE-')}
    expected_names = {'QA Atlas Packaging', 'QA Beacon Electronics', 'QA Cobalt Textiles', 'QA Delta Freight'}
    check('All four QA suppliers exist', expected_names <= qa.keys())
    check('All supplier statuses represented', {s['status'] for s in qa.values()} == {'active', 'onboarding', 'suspended', 'inactive'})
    check('Supplier search works', len(list_all('/suppliers?search=QA%20Atlas')) == 1)
    check('Supplier status filter works', all(s['status'] == 'onboarding' for s in list_all('/suppliers?status=onboarding')))

    commitments = list_all('/commitments')
    qa_commitments = [c for c in commitments if c['title'].startswith('QA ')]
    check('All commitment types represented', {c['commitment_type'] for c in qa_commitments} == {'price', 'delivery', 'quantity', 'quality', 'sla'})
    check('Pending, fulfilled, overdue, and breached states represented', {c['status'] for c in qa_commitments} == {'pending', 'fulfilled', 'overdue', 'breached'})
    check('Positive and negative savings calculated from stored values', any(c['savings'] == '25.00' for c in qa_commitments) and any(float(c['savings']) < 0 for c in qa_commitments if c['savings'] is not None))
    check('Commitment type filter works', all(c['commitment_type'] == 'quality' for c in list_all('/commitments?commitment_type=quality')))
    check('Missing required price value rejected', request('POST', '/commitments', {'supplier_id': qa['QA Atlas Packaging']['id'], 'commitment_type': 'price', 'title': 'QA invalid price'}, expected=422) is not None)
    check('Duplicate supplier rejected', request('POST', '/suppliers', {'name': 'QA Atlas Packaging', 'email': ''}, expected=409) is not None)
    check('Unknown supplier returns 404', request('GET', '/suppliers/999999999', expected=404) is not None)

    for name, supplier in qa.items():
        history = list_all(f"/suppliers/{supplier['id']}/performance")
        if not history:
            request('POST', f"/suppliers/{supplier['id']}/performance/snapshot", expected=201)
            history = list_all(f"/suppliers/{supplier['id']}/performance")
        check(f'Performance history available: {name}', bool(history))

    status = request('GET', '/memory/status')['data']
    mode = status['mode']
    check('Memory mode is explicit', mode in {'LOCAL_MOCK', 'CLOUD'})
    for name, supplier in qa.items():
        insights = request('GET', f"/memory/insights/{supplier['id']}")['data']
        for evidence in insights['evidence']:
            if evidence['sync_status'] in {'local_only', 'failed', 'pending'} and mode == 'CLOUD':
                result = request('POST', f"/memory/{evidence['id']}/retry")
                check(f"Hindsight synchronization: memory {evidence['id']}", result['data']['sync_status'] == 'synced')
        check(f'Traceable memory evidence: {name}', insights['memory_count'] >= 1)

    tokens = {
        'QA Atlas Packaging': ('QA-ATLAS-VOLUME', '8% discount'),
        'QA Beacon Electronics': ('QA-BEACON-LEADTIME', '21-day lead-time buffer'),
        'QA Cobalt Textiles': ('QA-COBALT-QUALITY', 'dye-lot variance'),
        'QA Delta Freight': ('QA-DELTA-ROUTES', 'Tuesday pickups'),
    }
    for name, (query, expected_fact) in tokens.items():
        supplier_id = qa[name]['id']
        recalled = request('GET', f'/memory/recall/{supplier_id}?' + urlencode({'query': query}))['data']
        contents = ' '.join(item['content'] for item in recalled['items'])
        check(f'Supplier-scoped recall: {name}', expected_fact in contents)
        check(f'Retrieval source is honest: {name}', recalled['source'] in ({'local_database'} if mode == 'LOCAL_MOCK' else {'hindsight_cloud', 'local_database_fallback'}))

    atlas_id = qa['QA Atlas Packaging']['id']
    subject = 'QA live automatic-learning check'
    interactions = list_all(f'/interactions?supplier_id={atlas_id}')
    if not any(i['subject'] == subject for i in interactions):
        created = request('POST', '/interactions', {'supplier_id': atlas_id, 'interaction_type': 'note', 'subject': subject, 'content': 'QA-LIVE-LEARNING: This fictional interaction verifies automatic source-to-memory retention.'}, expected=201)
        check('Interaction creates a linked memory', bool(created['meta']['memory_item_id']))
        expected_status = 'local_only' if mode == 'LOCAL_MOCK' else 'synced'
        if created['meta']['memory_status'] == 'failed' and mode == 'CLOUD':
            retried = request('POST', f"/memory/{created['meta']['memory_item_id']}/retry")
            check('Transient retain failure can be retried', retried['data']['sync_status'] == 'synced')
        else:
            check('Automatic memory uses the configured mode', created['meta']['memory_status'] == expected_status)
    else:
        check('Automatic-learning fixture already exists (idempotent rerun)')

    target = next(c for c in qa_commitments if c['title'] == 'QA independent verification target')
    if not target['verified_at']:
        verified = request('POST', f"/commitments/{target['id']}/verify", {'note': 'Live fictional independent verification by demo administrator.'})
        check('Independent verification persists', verified['data']['verified_by_id'] != verified['data']['created_by_id'])
    else:
        check('Independent verification is already persisted', target['verified_by_id'] != target['created_by_id'])

    temporary = request('POST', '/suppliers', {'name': f'QA-LIVE-CRUD-{datetime.now(timezone.utc).timestamp()}', 'email': ''}, expected=201)['data']
    try:
        changed = request('PATCH', f"/suppliers/{temporary['id']}", {'category': 'QA Updated', 'status': 'onboarding'})['data']
        check('Supplier update persists', changed['category'] == 'QA Updated' and changed['status'] == 'onboarding')
        commitment = request('POST', '/commitments', {'supplier_id': temporary['id'], 'commitment_type': 'delivery', 'title': 'QA-LIVE-CRUD commitment', 'deadline': (datetime.now(timezone.utc)+timedelta(days=5)).isoformat()}, expected=201)['data']
        updated = request('PATCH', f"/commitments/{commitment['id']}", {'title': 'QA-LIVE-CRUD updated commitment'})['data']
        check('Commitment create/read/update works', updated['title'] == 'QA-LIVE-CRUD updated commitment')
        request('POST', f"/commitments/{commitment['id']}/verify", {'note': 'Self verification must fail.'}, expected=403)
        check('Self-verification is rejected')
        request('DELETE', f"/commitments/{commitment['id']}", expected=204)
        check('Owned temporary commitment cleanup succeeds')
    finally:
        request('DELETE', f"/suppliers/{temporary['id']}", expected=204)
    check('Owned temporary supplier cleanup succeeds')

    dashboard = request('GET', '/dashboard/executive')['data']
    check('Dashboard uses live database totals', dashboard['suppliers']['total'] >= 4 and dashboard['commitments']['total'] >= 12)
    print(f'\n{len(PASSED)} live checks passed in {mode} mode.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'\nFAIL  {error}', file=sys.stderr)
        sys.exit(1)
