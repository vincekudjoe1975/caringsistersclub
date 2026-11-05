"""Iter55: editable Home page header (hero) fields on /api/home-content + /api/admin/home-content.
Backs up the real settings{key:'home'} doc and restores it exactly afterwards."""
import os
import copy
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
DB = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
TOK = 'qa_tok_iter55'
UID = 'qa_user_iter55'
COOKIES = {'session_token': TOK}

DEFAULTS = {
    'hero_kicker': 'Welcome to Caring Sisters Club',
    'hero_title': 'Connecting & Empowering Women of the Diaspora',
    'hero_subtitle': 'A powerful professional network fostering friendship, mutual respect, and philanthropic growth globally.',
    'hero_image_alt': 'Confident professional woman of the Diaspora in a magenta blazer',
    'hero_badge_number': '2,400+',
    'hero_badge_label': 'Sisters empowered',
    'hero_image': '',
}


@pytest.fixture(scope='module', autouse=True)
def setup_module_env():
    backup = DB.settings.find_one({'key': 'home'})
    DB.users.insert_one({'user_id': UID, 'email': 'qa55@example.com', 'name': 'QA55', 'role': 'admin'})
    DB.user_sessions.insert_one({'session_token': TOK, 'user_id': UID, 'expires_at': '2099-01-01T00:00:00+00:00'})
    yield
    DB.users.delete_one({'user_id': UID})
    DB.user_sessions.delete_one({'session_token': TOK})
    if backup:
        DB.settings.replace_one({'_id': backup['_id']}, backup, upsert=True)
    else:
        DB.settings.delete_one({'key': 'home'})


def _current():
    return requests.get(f'{BASE}/api/home-content').json()


def _put(payload, cookies=COOKIES):
    return requests.put(f'{BASE}/api/admin/home-content', json=payload, cookies=cookies, headers={'X-Requested-With': 'XMLHttpRequest'})


class TestHomeHero:
    def test_get_returns_hero_defaults_when_unset(self):
        doc = DB.settings.find_one({'key': 'home'}) or {}
        r = requests.get(f'{BASE}/api/home-content')
        assert r.status_code == 200
        d = r.json()
        for k, v in DEFAULTS.items():
            assert k in d, k
            if k not in doc:
                assert d[k] == v, (k, d[k])
        assert '_id' not in d

    def test_put_requires_admin(self):
        p = _current()
        assert _put(p, cookies={}).status_code in (401, 403)

    def test_put_saves_hero_fields_and_persists(self):
        p = _current()
        p.update(hero_kicker='TEST_ kicker', hero_title='TEST_ Big title', hero_subtitle='TEST_ subtitle',
                 hero_image='https://images.example.com/a.jpg', hero_image_alt='TEST_ alt',
                 hero_badge_number='3,000+', hero_badge_label='TEST_ sisters')
        r = _put(p)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['hero_title'] == 'TEST_ Big title'
        g = _current()
        for k in ('hero_kicker', 'hero_title', 'hero_subtitle', 'hero_image', 'hero_image_alt', 'hero_badge_number', 'hero_badge_label'):
            assert g[k] == p[k], k
        # mission fields untouched
        assert g['mission_title'] == p['mission_title']
        assert len(g['pillars']) == len(p['pillars'])

    def test_empty_optional_fields_hide_and_title_defaults(self):
        p = _current()
        p.update(hero_kicker='  ', hero_title='   ', hero_subtitle='', hero_badge_number='', hero_badge_label='', hero_image_alt='', hero_image='')
        r = _put(p)
        assert r.status_code == 200, r.text
        g = _current()
        assert g['hero_title'] == DEFAULTS['hero_title']
        assert g['hero_kicker'] == '' and g['hero_subtitle'] == '' and g['hero_badge_number'] == ''
        assert g['hero_badge_label'] == '' and g['hero_image_alt'] == '' and g['hero_image'] == ''

    def test_max_lengths_truncate(self):
        p = _current()
        p.update(hero_kicker='K' * 200, hero_title='T' * 300, hero_subtitle='S' * 500,
                 hero_image_alt='A' * 300, hero_badge_number='9' * 50, hero_badge_label='L' * 80)
        assert _put(p).status_code == 200
        g = _current()
        assert len(g['hero_kicker']) == 80 and len(g['hero_title']) == 140 and len(g['hero_subtitle']) == 300
        assert len(g['hero_image_alt']) == 160 and len(g['hero_badge_number']) == 20 and len(g['hero_badge_label']) == 40

    def test_invalid_hero_image_rejected(self):
        before = _current()
        for bad in ('http://insecure.example.com/a.jpg', 'javascript:alert(1)', '/etc/passwd'):
            p = copy.deepcopy(before)
            p['hero_image'] = bad
            r = _put(p)
            assert r.status_code == 400, bad
            assert 'Header photo' in r.json().get('detail', '')
        assert _current()['hero_image'] == before['hero_image']

    def test_uploaded_media_path_accepted(self):
        p = _current()
        p['hero_image'] = '/api/media/file/abc-123'
        assert _put(p).status_code == 200
        assert _current()['hero_image'] == '/api/media/file/abc-123'

    def test_legacy_payload_without_hero_fields(self):
        """A client that omits hero fields (old cached admin bundle) - document behaviour."""
        p = {k: v for k, v in _current().items() if not k.startswith('hero_')}
        r = _put(p)
        assert r.status_code == 200
        g = _current()
        assert g['hero_title'] == DEFAULTS['hero_title']
        # NOTE: optional fields become '' (hidden), not defaults
        print('legacy payload result kicker=%r badge=%r' % (g['hero_kicker'], g['hero_badge_number']))
