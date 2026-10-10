"""iteration 13 — waitlist position/status, admin waitlist actions, YIR ask_amount, volunteer certificates."""
import os
import time
import secrets as _s
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = BASE_URL + '/api'
PROG_SLUG = 'wellness-workshops'
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


def _admin():
    s = requests.Session()
    s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
    s.cookies.set('session_token', 'qa_tok_123')
    return s


def _public():
    s = requests.Session()
    s.headers.update({'Content-Type': 'application/json'})
    return s


def _pid():
    return db.programs.find_one({'slug': PROG_SLUG}, {'id': 1})['id']


@pytest.fixture(scope='module', autouse=True)
def setup_program():
    # Capacity=1, waitlist_mode=claim
    db.programs.update_one({'slug': PROG_SLUG}, {'$set': {'capacity': 1, 'waitlist_mode': 'claim'}})
    # Clear prior submissions for this program
    db.submissions.delete_many({'type': 'program_signup', 'program_id': _pid(), 'data.email': {'$regex': 'qa\\.iter13.*@example\\.com$'}})
    yield
    db.submissions.delete_many({'type': 'program_signup', 'program_id': _pid(), 'data.email': {'$regex': 'qa\\.iter13.*@example\\.com$'}})
    db.programs.update_one({'slug': PROG_SLUG}, {'$set': {'capacity': 0, 'waitlist_mode': 'claim'}})


class TestWaitlistPositionAndStatus:
    tokens = {}

    def _signup(self, letter, delay=1.2):
        # One signup per second IP rate limit (5/min) is fine.
        time.sleep(delay)
        em = f'qa.iter13.{letter}.{int(time.time()*1000)}@example.com'
        r = _public().post(f'{API}/programs/{PROG_SLUG}/signup', json={
            'name': f'QA Iter13 {letter.upper()}', 'email': em, 'phone': '', 'message': ''
        })
        return r, em

    def test_a_seats_first(self):
        r, _ = self._signup('a')
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['waitlist'] is False

    def test_b_waitlisted_position_1(self):
        r, em = self._signup('b')
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['waitlist'] is True
        assert d['position'] == 1
        assert d['total'] == 1
        assert isinstance(d.get('status_token'), str) and len(d['status_token']) > 10
        TestWaitlistPositionAndStatus.tokens['B'] = d['status_token']
        TestWaitlistPositionAndStatus.tokens['B_email'] = em

    def test_c_waitlisted_position_2(self):
        r, em = self._signup('c')
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['waitlist'] is True and d['position'] == 2 and d['total'] == 2
        TestWaitlistPositionAndStatus.tokens['C'] = d['status_token']
        TestWaitlistPositionAndStatus.tokens['C_email'] = em

    def test_status_waiting(self):
        tok = TestWaitlistPositionAndStatus.tokens['C']
        r = _public().get(f'{API}/waitlist/status', params={'token': tok})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['status'] == 'waiting'
        assert d['position'] == 2
        assert d['total'] == 2

    def test_status_invalid_token(self):
        r = _public().get(f'{API}/waitlist/status', params={'token': 'bogus_' + _s.token_urlsafe(8)})
        assert r.status_code == 404

    def test_admin_waitlist_list_unauth(self):
        r = requests.get(f'{API}/admin/programs/{_pid()}/waitlist')
        assert r.status_code in (401, 403)

    def test_admin_waitlist_list(self):
        r = _admin().get(f'{API}/admin/programs/{_pid()}/waitlist')
        assert r.status_code == 200, r.text
        d = r.json()
        items = d['items']
        assert len(items) >= 2
        assert items[0]['position'] == 1 and items[1]['position'] == 2
        for it in items[:2]:
            assert it['email'] and it['name'] and it['joined']
            assert it['offer_status'] == 'waiting'

    def test_offer_c_staff_override(self):
        # Find C's submission id
        c_email = TestWaitlistPositionAndStatus.tokens['C_email']
        sub = db.submissions.find_one({'data.email': c_email})
        assert sub
        sid = sub['id']
        r = _admin().post(f'{API}/admin/waitlist/{sid}/offer')
        assert r.status_code == 200, r.text
        assert 'offer_expires' in r.json()
        # DB check
        time.sleep(0.5)
        s2 = db.submissions.find_one({'id': sid})
        assert s2['offer_status'] == 'open'
        assert s2.get('offer_override') is True
        assert s2.get('offer_token')
        # Status endpoint shows offer
        tok = TestWaitlistPositionAndStatus.tokens['C']
        r = _public().get(f'{API}/waitlist/status', params={'token': tok})
        d = r.json()
        assert d['status'] == 'offer'
        assert d['claim_token'] == s2['offer_token']
        TestWaitlistPositionAndStatus.tokens['C_claim'] = s2['offer_token']

    def test_claim_override_full(self):
        # Program is full (A seated). But offer_override bypasses seat check.
        claim_tok = TestWaitlistPositionAndStatus.tokens['C_claim']
        r = _public().post(f'{API}/waitlist/claim', json={'token': claim_tok})
        assert r.status_code == 200, r.text
        assert r.json()['status'] == 'claimed'
        time.sleep(0.5)
        sub = db.submissions.find_one({'data.email': TestWaitlistPositionAndStatus.tokens['C_email']})
        assert sub['waitlist'] is False
        assert sub['offer_status'] == 'claimed'

    def test_movein_b(self):
        sub = db.submissions.find_one({'data.email': TestWaitlistPositionAndStatus.tokens['B_email']})
        sid = sub['id']
        r = _admin().post(f'{API}/admin/waitlist/{sid}/move-in')
        assert r.status_code == 200, r.text
        time.sleep(0.3)
        sub2 = db.submissions.find_one({'id': sid})
        assert sub2['waitlist'] is False
        # Status for B
        r2 = _public().get(f'{API}/waitlist/status', params={'token': TestWaitlistPositionAndStatus.tokens['B']})
        assert r2.status_code == 200
        assert r2.json()['status'] == 'in'

    def test_remove_action(self):
        # Add a fresh D on waitlist (program is now actually: A seated, B moved-in=False? B is now not-waitlist, so capacity 1 with 2 enrolled; next signup will waitlist)
        r, em = self._signup('d')
        assert r.status_code == 200
        d = r.json()
        assert d['waitlist'] is True
        tok_d = d['status_token']
        sub = db.submissions.find_one({'data.email': em})
        sid = sub['id']
        r2 = _admin().post(f'{API}/admin/waitlist/{sid}/remove')
        assert r2.status_code == 200
        time.sleep(0.3)
        s2 = db.submissions.find_one({'id': sid})
        assert s2['stage'] == 'not_fit'
        r3 = _public().get(f'{API}/waitlist/status', params={'token': tok_d})
        assert r3.status_code == 200
        assert r3.json()['status'] == 'removed'

    def test_invalid_action(self):
        sub = db.submissions.find_one({'data.email': TestWaitlistPositionAndStatus.tokens['C_email']})
        r = _admin().post(f"{API}/admin/waitlist/{sub['id']}/foobar")
        assert r.status_code == 400

    def test_non_waitlisted_404(self):
        r = _admin().post(f'{API}/admin/waitlist/nonexistent_sid/offer')
        assert r.status_code == 404


# ---------- YIR ask_amount ----------
class TestYirAskAmount:
    def test_put_ask_amount(self):
        r = _admin().put(f'{API}/admin/year-in-review/2026', json={'ask_amount': 75})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get('ask_amount') == 75

    def test_put_ask_amount_zero_rejected(self):
        r = _admin().put(f'{API}/admin/year-in-review/2026', json={'ask_amount': 0})
        assert r.status_code == 400

    def test_get_admin_includes_ask(self):
        r = _admin().get(f'{API}/admin/year-in-review/2026')
        assert r.status_code == 200
        assert r.json().get('ask_amount') == 75

    def test_published_public_has_ask(self):
        # publish
        r = _admin().put(f'{API}/admin/year-in-review/2026', json={'public': True})
        assert r.status_code == 200
        try:
            r2 = _public().get(f'{API}/year-in-review/2026')
            assert r2.status_code == 200
            assert r2.json().get('ask_amount') == 75
        finally:
            _admin().put(f'{API}/admin/year-in-review/2026', json={'public': False})

    def test_email_html_has_donate_link(self):
        r = _admin().get(f'{API}/admin/year-in-review/2026/email')
        assert r.status_code == 200
        assert '/donate?amount=75' in r.json()['html']


# ---------- Certificates ----------
class TestCertificates:
    cert_token = 'qa_tok_cert_iter13'
    email = 'qa.iter13.cert@example.com'

    @classmethod
    def setup_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})
        db.volunteer_milestones.insert_one({
            'email': cls.email, 'scope': 'all', 'threshold': 50, 'label': '50 Hours All-Time',
            'awarded_at': '2026-01-01T00:00:00+00:00', 'cert_token': cls.cert_token
        })
        db.volunteer_hours.insert_one({
            'id': 'qa_vh_cert_iter13', 'email': cls.email, 'name': 'QA Cert Iter13',
            'status': 'approved', 'hours': 50, 'date': '2026-01-01', 'created_at': '2026-01-01T00:00:00+00:00'
        })

    @classmethod
    def teardown_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})

    def test_pdf_download(self):
        r = _public().get(f'{API}/certificates/{self.cert_token}.pdf')
        assert r.status_code == 200, r.text
        assert r.headers['content-type'].startswith('application/pdf')
        assert r.content[:4] == b'%PDF'

    def test_pdf_bad_token(self):
        r = _public().get(f'{API}/certificates/not_a_real_token_xyz.pdf')
        assert r.status_code == 404

    def test_request_invalid_email(self):
        r = _public().post(f'{API}/certificates/request', json={'email': 'bad'})
        assert r.status_code == 400

    def test_request_valid_email_generic(self):
        r = _public().post(f'{API}/certificates/request', json={'email': self.email})
        assert r.status_code == 200
        assert 'badge' in r.json()['message'].lower() or 'sent' in r.json()['message'].lower()

    def test_request_assigns_token_if_missing(self):
        em = 'qa.iter13.cert2@example.com'
        db.volunteer_milestones.delete_many({'email': em})
        db.volunteer_milestones.insert_one({'email': em, 'scope': 'all', 'threshold': 50, 'label': '50h', 'awarded_at': '2026-01-01T00:00:00+00:00', 'cert_token': None})
        try:
            r = _public().post(f'{API}/certificates/request', json={'email': em})
            assert r.status_code == 200
            m = db.volunteer_milestones.find_one({'email': em})
            assert m.get('cert_token')
        finally:
            db.volunteer_milestones.delete_many({'email': em})

    def test_request_rate_limit(self):
        # 3/10min per IP. We've already consumed 2 valid + 1 invalid above this run. Fire a few extras.
        got_429 = False
        for _ in range(6):
            r = _public().post(f'{API}/certificates/request', json={'email': 'qa.iter13.rl@example.com'})
            if r.status_code == 429:
                got_429 = True
                break
        assert got_429, 'Expected 429 from /certificates/request within 10 min'


# ---------- Milestone award writes cert_token ----------
class TestMilestoneAward:
    email = 'qa.iter13.award@example.com'
    vh_id = None

    @classmethod
    def setup_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})
        import uuid
        cls.vh_id = str(uuid.uuid4())
        db.volunteer_hours.insert_one({
            'id': cls.vh_id, 'email': cls.email, 'name': 'QA Award', 'hours': 51,
            'date': '2026-01-01', 'status': 'pending', 'created_at': '2026-01-01T00:00:00+00:00',
            'program': 'Wellness'
        })

    @classmethod
    def teardown_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})

    def test_approve_awards_milestone_with_cert_token(self):
        r = _admin().post(f'{API}/admin/volunteer-hours/{self.vh_id}/approve')
        assert r.status_code == 200, r.text
        time.sleep(1.5)
        # 50h milestones should have cert_token; 10h should not
        m50 = list(db.volunteer_milestones.find({'email': self.email, 'threshold': 50}))
        m10 = list(db.volunteer_milestones.find({'email': self.email, 'threshold': 10}))
        assert m50 and all(m.get('cert_token') for m in m50), f'50h milestones missing cert_token: {m50}'
        assert m10 and all(m.get('cert_token') is None for m in m10), f'10h milestones should not have cert_token: {m10}'
