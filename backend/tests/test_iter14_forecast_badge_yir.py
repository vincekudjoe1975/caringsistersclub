"""iteration 14 — program forecast, waitlist alerts, badge sharing, YIR gift attribution."""
import os
import re
import time
import uuid
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


# ---------- Program forecast + settings ----------
class TestForecastEndpoint:
    def test_unauth_401(self):
        r = requests.get(f'{API}/admin/reports/program-forecast')
        assert r.status_code in (401, 403)

    def test_admin_shape(self):
        r = _admin().get(f'{API}/admin/reports/program-forecast')
        assert r.status_code == 200, r.text
        d = r.json()
        assert 'items' in d and isinstance(d['items'], list)
        s = d['settings']
        for k in ('wl_alert_mode', 'wl_alert_threshold', 'forecast_weekly'):
            assert k in s
        if d['items']:
            it = d['items'][0]
            for k in ('capacity', 'taken', 'fill_pct', 'weekly', 'rate', 'days_to_fill', 'waitlist', 'flag', 'reason'):
                assert k in it, f'missing {k}'
            assert isinstance(it['weekly'], list) and len(it['weekly']) == 4
            assert all(isinstance(x, int) for x in it['weekly'])


class TestForecastFlags:
    emails = []

    @classmethod
    def setup_class(cls):
        db.programs.update_one({'slug': PROG_SLUG}, {'$set': {'capacity': 2, 'waitlist_mode': 'claim'}})
        db.submissions.delete_many({'data.email': {'$regex': 'qa\\.iter14.*@example\\.com$'}})

    @classmethod
    def teardown_class(cls):
        db.submissions.delete_many({'data.email': {'$regex': 'qa\\.iter14.*@example\\.com$'}})
        db.programs.update_one({'slug': PROG_SLUG}, {'$set': {'capacity': 0, 'waitlist_mode': 'claim'}})

    def _signup(self, tag):
        em = f'qa.iter14.{tag}.{int(time.time()*1000)}@example.com'
        self.__class__.emails.append(em)
        time.sleep(1.3)
        r = _public().post(f'{API}/programs/{PROG_SLUG}/signup',
                           json={'name': f'QA Iter14 {tag}', 'email': em, 'phone': '', 'message': ''})
        return r

    def test_fill_capacity_and_waitlist_flag(self):
        # 2 seats fill + 1 waitlisted
        r1 = self._signup('s1'); assert r1.status_code == 200, r1.text
        r2 = self._signup('s2'); assert r2.status_code == 200, r2.text
        r3 = self._signup('w1'); assert r3.status_code == 200, r3.text
        assert r3.json().get('waitlist') is True
        time.sleep(2.5)
        r = _admin().get(f'{API}/admin/reports/program-forecast')
        assert r.status_code == 200
        row = next(x for x in r.json()['items'] if x['title'])
        # find the wellness-workshops row
        pid = _pid()
        row = next(x for x in r.json()['items'] if x['id'] == pid)
        assert row['capacity'] == 2
        assert row['taken'] == 2
        assert row['fill_pct'] == 100
        assert row['days_to_fill'] == 0
        assert row['waitlist'] >= 1
        assert row['flag'] is True
        assert row['reason']  # non-empty

    def test_capacity_zero_fill_pct_null_flag_false(self):
        # programs with capacity 0 should have fill_pct None, flag False
        # pick any other published prog with cap 0
        r = _admin().get(f'{API}/admin/reports/program-forecast')
        items = r.json()['items']
        zeros = [x for x in items if (x['capacity'] or 0) == 0]
        if not zeros:
            pytest.skip('no capacity=0 programs available')
        for z in zeros:
            assert z['fill_pct'] is None
            assert z['flag'] is False


class TestForecastSettings:
    def test_valid_persist(self):
        r = _admin().put(f'{API}/admin/reports/forecast-settings',
                         json={'wl_alert_mode': 'threshold', 'wl_alert_threshold': 3, 'forecast_weekly': False})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['wl_alert_mode'] == 'threshold'
        assert d['wl_alert_threshold'] == 3
        assert d['forecast_weekly'] is False
        # Verify via GET
        r2 = _admin().get(f'{API}/admin/reports/program-forecast')
        s = r2.json()['settings']
        assert s['wl_alert_mode'] == 'threshold'
        assert s['wl_alert_threshold'] == 3
        assert s['forecast_weekly'] is False

    def test_invalid_mode(self):
        r = _admin().put(f'{API}/admin/reports/forecast-settings',
                         json={'wl_alert_mode': 'bogus', 'wl_alert_threshold': 3, 'forecast_weekly': False})
        assert r.status_code == 400

    def test_invalid_threshold_zero(self):
        r = _admin().put(f'{API}/admin/reports/forecast-settings',
                         json={'wl_alert_mode': 'threshold', 'wl_alert_threshold': 0, 'forecast_weekly': False})
        assert r.status_code == 400

    def test_reset_defaults(self):
        r = _admin().put(f'{API}/admin/reports/forecast-settings',
                         json={'wl_alert_mode': 'instant', 'wl_alert_threshold': 5, 'forecast_weekly': True})
        assert r.status_code == 200


class TestForecastSend:
    def test_send(self):
        r = _admin().post(f'{API}/admin/reports/program-forecast/send')
        # 502 acceptable if provider rejects; otherwise 200 with {flagged, sent}
        assert r.status_code in (200, 502), r.text
        if r.status_code == 200:
            d = r.json()
            assert 'flagged' in d and 'sent' in d


# ---------- Badges ----------
class TestBadges:
    email = 'qa.badge@example.com'
    tok = 'qa_share_1'

    @classmethod
    def setup_class(cls):
        db.volunteer_milestones.delete_many({'share_token': cls.tok})
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})
        db.volunteer_milestones.insert_one({
            'email': cls.email, 'scope': 'all', 'threshold': 50,
            'label': '50 Hours All-Time', 'awarded_at': '2026-01-01T00:00:00+00:00',
            'share_token': cls.tok,
        })
        db.volunteer_hours.insert_one({
            'id': str(uuid.uuid4()), 'email': cls.email, 'name': 'Ama Owusu Mensah',
            'status': 'approved', 'hours': 50, 'date': '2026-01-01',
            'created_at': '2026-01-01T00:00:00+00:00',
        })

    @classmethod
    def teardown_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})

    def test_badge_json(self):
        r = _public().get(f'{API}/badges/{self.tok}')
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['name'] == 'Ama M.'
        assert d['threshold'] == 50
        assert d['label']
        assert 'email' not in d

    def test_badge_bad_token(self):
        r = _public().get(f'{API}/badges/does_not_exist_xyz')
        assert r.status_code == 404

    def test_badge_card_png(self):
        r = _public().get(f'{API}/share/badge/{self.tok}/card.png')
        assert r.status_code == 200
        assert r.headers['content-type'].startswith('image/png')
        assert r.content[:4] == b'\x89PNG'

    def test_badge_share_html(self):
        r = _public().get(f'{API}/share/badge/{self.tok}')
        assert r.status_code == 200
        body = r.text
        assert 'og:image' in body
        assert f'/api/share/badge/{self.tok}/card.png' in body
        assert f'/badge/{self.tok}' in body
        assert 'meta http-equiv="refresh"' in body


# ---------- Milestone share_token assignment ----------
class TestMilestoneShareToken:
    email = 'qa.iter14.share@example.com'
    vh_id = None

    @classmethod
    def setup_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})
        cls.vh_id = str(uuid.uuid4())
        db.volunteer_hours.insert_one({
            'id': cls.vh_id, 'email': cls.email, 'name': 'QA Share',
            'hours': 51, 'date': '2026-01-01', 'status': 'pending',
            'created_at': '2026-01-01T00:00:00+00:00', 'program': 'Wellness',
        })

    @classmethod
    def teardown_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_hours.delete_many({'email': cls.email})

    def test_approve_awards_share_token(self):
        r = _admin().post(f'{API}/admin/volunteer-hours/{self.vh_id}/approve')
        assert r.status_code == 200, r.text
        time.sleep(1.8)
        all_m = list(db.volunteer_milestones.find({'email': self.email}))
        assert all_m
        for m in all_m:
            assert m.get('share_token'), f'milestone missing share_token: {m}'


class TestCertRequestAssignsShareToken:
    email = 'qa.iter14.cert_share@example.com'

    @classmethod
    def setup_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})
        db.volunteer_milestones.insert_one({
            'email': cls.email, 'scope': 'all', 'threshold': 50,
            'label': '50h', 'awarded_at': '2026-01-01T00:00:00+00:00',
            'cert_token': 'qa_cert_share_tok', 'share_token': None,
        })

    @classmethod
    def teardown_class(cls):
        db.volunteer_milestones.delete_many({'email': cls.email})

    def test_cert_request_assigns_share_token(self):
        r = _public().post(f'{API}/certificates/request', json={'email': self.email})
        # Might be rate-limited if other tests ran; accept 200 or 429
        if r.status_code == 429:
            pytest.skip('rate-limited')
        assert r.status_code == 200, r.text
        time.sleep(0.5)
        m = db.volunteer_milestones.find_one({'email': self.email})
        assert m.get('share_token')


# ---------- YIR gift attribution ----------
class TestYirAttribution:
    year = 2026

    @classmethod
    def setup_class(cls):
        # Clear counters & QA txns
        db.yir_clicks.delete_many({'year': cls.year})
        db.payment_transactions.delete_many({'donor_email': {'$regex': 'qa\\.iter14\\.yir.*@example\\.com$'}})

    @classmethod
    def teardown_class(cls):
        db.yir_clicks.delete_many({'year': cls.year})
        db.payment_transactions.delete_many({'donor_email': {'$regex': 'qa\\.iter14\\.yir.*@example\\.com$'}})

    def test_email_track_redirect(self):
        r = _public().get(f'{API}/t/yir/{self.year}/email', params={'amount': 75}, allow_redirects=False)
        assert r.status_code == 302
        loc = r.headers['location']
        assert f'src=yir-email-{self.year}' in loc
        assert 'amount=75' in loc
        assert '/donate' in loc

    def test_page_click_increments(self):
        r = _public().post(f'{API}/yir/{self.year}/click')
        assert r.status_code == 200
        time.sleep(0.3)
        c = db.yir_clicks.find_one({'year': self.year, 'source': 'page'})
        assert c and c.get('clicks', 0) >= 1

    def test_checkout_stores_yir_source(self):
        em = f'qa.iter14.yir.{int(time.time()*1000)}@example.com'
        r = _public().post(f'{API}/payments/checkout', json={
            'amount': 25, 'frequency': 'one-time', 'donor_name': 'QA YIR',
            'donor_email': em, 'anonymous': False,
            'origin_url': BASE_URL, 'source': f'yir-page-{self.year}'
        })
        if r.status_code == 429:
            pytest.skip('rate limited')
        assert r.status_code == 200, r.text
        sid = r.json()['session_id']
        time.sleep(0.3)
        t = db.payment_transactions.find_one({'session_id': sid})
        assert t['source'] == f'yir-page-{self.year}'

    def test_checkout_invalid_source_becomes_null(self):
        em = f'qa.iter14.yir.evil.{int(time.time()*1000)}@example.com'
        r = _public().post(f'{API}/payments/checkout', json={
            'amount': 25, 'frequency': 'one-time', 'donor_name': 'QA YIR',
            'donor_email': em, 'anonymous': False,
            'origin_url': BASE_URL, 'source': 'evil'
        })
        if r.status_code == 429:
            pytest.skip('rate limited')
        assert r.status_code == 200, r.text
        sid = r.json()['session_id']
        time.sleep(0.3)
        t = db.payment_transactions.find_one({'session_id': sid})
        assert t['source'] is None

    def test_yir_results_shape(self):
        r = _admin().get(f'{API}/admin/year-in-review/{self.year}/results')
        assert r.status_code == 200, r.text
        d = r.json()
        for src in ('email', 'page'):
            assert src in d
            for k in ('clicks', 'checkouts', 'gifts', 'raised', 'conversion'):
                assert k in d[src], f'{src} missing {k}'
