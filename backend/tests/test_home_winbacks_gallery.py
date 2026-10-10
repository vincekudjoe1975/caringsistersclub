"""Backend tests: home-content, win-backs, program gallery/testimonials/home picks."""
import os
import re
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') if False else os.environ.get('REACT_APP_BACKEND_URL', 'https://caring-sisters-clone.preview.emergentagent.com').rstrip('/')
# use preview URL explicitly from frontend env
with open('/app/frontend/.env') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE = line.split('=', 1)[1].strip().rstrip('/')
            break

MONGO = MongoClient(os.environ['MONGO_URL'])
DB = MONGO[os.environ['DB_NAME']]

ADMIN_COOKIE = {'session_token': 'qa_tok_123'}
ADMIN_HEADERS = {'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json'}


@pytest.fixture(scope='module', autouse=True)
def cleanup_module():
    yield
    DB.settings.delete_one({'key': 'home'})
    DB.programs.delete_many({'title': {'$regex': '^QA '}})
    DB.cancellations.delete_many({'id': {'$in': ['qa_c1', 'qa_c2']}})
    DB.payment_transactions.delete_many({'session_id': 'qa_wb_txn'})


# ---------- home-content ----------
class TestHomeContent:
    def test_public_defaults(self):
        DB.settings.delete_one({'key': 'home'})
        r = requests.get(f'{BASE}/api/home-content')
        assert r.status_code == 200
        d = r.json()
        assert d['mission_title']
        assert len(d['pillars']) == 3
        ids = [t['id'] for t in d['testimonials']]
        assert set(ids) == {'t-adaeze', 't-louise', 't-chantal'}

    def test_admin_requires_auth(self):
        r = requests.put(f'{BASE}/api/admin/home-content', json={}, headers=ADMIN_HEADERS)
        assert r.status_code in (401, 403)

    def test_update_rejects_invalid_card_link(self):
        payload = {
            'mission_heading': 'Our Mission',
            'mission_title': 'Test Title',
            'mission_body': 'Body paragraph for test.',
            'mission_quote': 'Quote here',
            'mission_image': '',
            'pillars': [{'icon': 'Briefcase', 'title': 'T', 'text': 'x', 'cta': 'Go', 'to': 'javascript:x'}],
            'testimonials': [],
        }
        r = requests.put(f'{BASE}/api/admin/home-content', json=payload, headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 400
        assert 'site path' in r.json()['detail'].lower() or 'https' in r.json()['detail'].lower()

    def test_update_rejects_empty_title(self):
        payload = {'mission_title': '', 'mission_body': 'x', 'mission_image': '', 'pillars': [{'title': 'T'}], 'testimonials': []}
        r = requests.put(f'{BASE}/api/admin/home-content', json=payload, headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 400

    def test_update_rejects_pillars_zero(self):
        payload = {'mission_title': 'A', 'mission_body': 'B', 'mission_image': '', 'pillars': [], 'testimonials': []}
        r = requests.put(f'{BASE}/api/admin/home-content', json=payload, headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 400

    def test_update_persists_and_public_reflects(self):
        payload = {
            'mission_heading': 'QA Heading',
            'mission_title': 'QA Mission Title',
            'mission_body': 'QA mission body paragraph.',
            'mission_quote': 'QA quote',
            'mission_image': 'https://images.unsplash.com/test.jpg',
            'pillars': [
                {'icon': 'Briefcase', 'title': 'QA Card 1', 'text': 'c1', 'cta': 'Go', 'to': '/donate'},
                {'icon': 'Home', 'title': 'QA Card 2', 'text': 'c2', 'cta': 'Learn', 'to': '/initiatives'},
            ],
            'testimonials': [
                {'id': 't-adaeze', 'quote': 'AQ', 'name': 'Ada', 'role': 'Grad', 'photo_url': ''},
                {'quote': 'QA quote NEW', 'name': 'QA Name', 'role': 'QA Role', 'photo_url': 'https://x.co/p.jpg'},
            ],
        }
        r = requests.put(f'{BASE}/api/admin/home-content', json=payload, headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['mission_title'] == 'QA Mission Title'
        assert len(d['pillars']) == 2
        assert d['pillars'][0]['title'] == 'QA Card 1'
        assert len(d['testimonials']) == 2
        assert d['updated_at']
        # public reflects
        p = requests.get(f'{BASE}/api/home-content').json()
        assert p['mission_title'] == 'QA Mission Title'
        assert p['testimonials'][1]['name'] == 'QA Name'


# ---------- Programs gallery / testimonials / home picks ----------
class TestProgramGallery:
    pid = None
    slug = None

    def _payload(self, **over):
        base = {
            'title': 'QA Gallery Program',
            'category': 'Community',
            'image_url': 'https://images.unsplash.com/photo-1593113616828-6f22bca04804',
            'summary': 'summary',
            'body': 'body',
            'goals': ['g1'],
            'impact': [{'value': '10', 'label': 'members'}],
            'cta_text': 'Join',
            'cta_link': '/volunteer',
            'published': True,
            'gallery': [
                {'url': 'https://images.unsplash.com/a.jpg', 'caption': 'Photo A'},
                {'url': 'https://images.unsplash.com/b.jpg', 'caption': 'Photo B'},
            ],
            'testimonials': [{'quote': 'Great prog', 'name': 'Jane Doe', 'role': 'Member', 'photo_url': ''}],
            'home_testimonial_ids': ['t-louise'],
        }
        base.update(over)
        return base

    def test_create_program_with_gallery_and_testimonials(self):
        r = requests.post(f'{BASE}/api/admin/programs', json=self._payload(), headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 200, r.text
        p = r.json()
        TestProgramGallery.pid = p['id']
        TestProgramGallery.slug = p['slug']
        assert len(p['gallery']) == 2
        assert p['gallery'][0]['caption'] == 'Photo A'
        assert len(p['testimonials']) == 1
        assert p['home_testimonial_ids'] == ['t-louise']

    def test_public_detail_merges_home_testimonial(self):
        assert TestProgramGallery.slug
        r = requests.get(f'{BASE}/api/programs/{TestProgramGallery.slug}')
        assert r.status_code == 200
        p = r.json()
        assert len(p['gallery']) == 2
        # custom + merged home testimonial
        names = [t['name'] for t in p['testimonials']]
        assert 'Jane Doe' in names
        assert 'Louise M.' in names

    def test_reject_bad_gallery_url(self):
        r = requests.post(f'{BASE}/api/admin/programs',
                          json=self._payload(title='QA Bad Gallery',
                                             gallery=[{'url': 'http://insecure/x.jpg', 'caption': 'bad'}]),
                          headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 400

    def test_reject_testimonial_missing_name(self):
        r = requests.post(f'{BASE}/api/admin/programs',
                          json=self._payload(title='QA Bad Testi',
                                             testimonials=[{'quote': 'x', 'name': '', 'role': '', 'photo_url': ''}]),
                          headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 400

    def test_update_removes_gallery_and_homepick(self):
        assert TestProgramGallery.pid
        r = requests.put(f'{BASE}/api/admin/programs/{TestProgramGallery.pid}',
                         json=self._payload(gallery=[{'url': 'https://images.unsplash.com/c.jpg', 'caption': 'Only C'}],
                                            home_testimonial_ids=[]),
                         headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        d = r.json()
        assert len(d['gallery']) == 1 and d['gallery'][0]['caption'] == 'Only C'
        # verify public reflects
        p = requests.get(f'{BASE}/api/programs/{TestProgramGallery.slug}').json()
        names = [t['name'] for t in p['testimonials']]
        assert 'Louise M.' not in names
        assert 'Jane Doe' in names

    def test_delete_program(self):
        if TestProgramGallery.pid:
            r = requests.delete(f'{BASE}/api/admin/programs/{TestProgramGallery.pid}', headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
            assert r.status_code == 200


# ---------- Win-Backs ----------
class TestWinBacks:
    def test_empty_state(self):
        DB.cancellations.delete_many({'id': {'$in': ['qa_c1', 'qa_c2']}})
        DB.payment_transactions.delete_many({'session_id': 'qa_wb_txn'})
        r = requests.get(f'{BASE}/api/admin/winbacks', headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        # may include other existing cancellations, so we only check structure
        d = r.json()
        assert set(d.keys()) >= {'cancellations', 'notes_sent', 'returned', 'rate', 'recovered', 'items'}

    def test_seeded_scenario(self):
        # Clean other cancellations/txns to isolate
        DB.cancellations.delete_many({'id': {'$in': ['qa_c1', 'qa_c2']}})
        DB.payment_transactions.delete_many({'session_id': 'qa_wb_txn'})
        # Capture baseline
        baseline = requests.get(f'{BASE}/api/admin/winbacks', headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE).json()
        b_cancel = baseline['cancellations']
        b_notes = baseline['notes_sent']
        b_returned = baseline['returned']
        b_recovered = baseline['recovered']

        DB.cancellations.insert_one({
            'id': 'qa_c1', 'sub_id': 'sub_qa_wb', 'email': 'qa.wb@example.com', 'name': 'QA WB',
            'amount': 20, 'ends_on': '', 'reason': '', 'token': 'qa_wb_tok',
            'thanked': True, 'thanked_at': '2026-01-01T00:00:00+00:00',
            'created_at': '2025-12-30T00:00:00+00:00',
        })
        DB.cancellations.insert_one({
            'id': 'qa_c2', 'sub_id': 'sub_qa_wb2', 'email': 'qa.wb2@example.com', 'name': 'QA WB2',
            'amount': 10, 'thanked': False, 'token': 'qa_wb_tok2',
            'created_at': '2025-12-29T00:00:00+00:00',
        })
        DB.payment_transactions.insert_one({
            'session_id': 'qa_wb_txn', 'donor_email': 'QA.WB@example.com', 'amount': 35,
            'payment_status': 'paid', 'frequency': 'one-time',
            'created_at': '2026-02-01T00:00:00+00:00', 'updated_at': '2026-02-01T00:00:00+00:00',
        })

        r = requests.get(f'{BASE}/api/admin/winbacks', headers=ADMIN_HEADERS, cookies=ADMIN_COOKIE)
        assert r.status_code == 200
        d = r.json()
        assert d['cancellations'] == b_cancel + 2
        assert d['notes_sent'] == b_notes + 1
        assert d['returned'] == b_returned + 1
        assert round(d['recovered'] - b_recovered, 2) == 35.0
        # QA items present
        qa_items = [i for i in d['items'] if i['email'] in ('qa.wb@example.com', 'qa.wb2@example.com')]
        assert len(qa_items) == 2
        qa1 = next(i for i in qa_items if i['email'] == 'qa.wb@example.com')
        qa2 = next(i for i in qa_items if i['email'] == 'qa.wb2@example.com')
        assert qa1['returned'] is True
        assert qa1['recovered'] == 35.0
        assert qa2['returned'] is False
        assert qa2['thanked'] is False
