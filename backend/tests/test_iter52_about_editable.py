"""Iteration 52 — fully editable About page (GET /api/about-content, PUT /api/admin/about-content).
Uses QA admin cookie session_token=qa_tok_123 (qa_session.py). Original settings.about doc is restored at teardown."""
import os
import copy
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"
XHR = {"X-Requested-With": "XMLHttpRequest"}
ADMIN = {"session_token": "qa_tok_123"}
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

TEXT_KEYS = ["hero_kicker", "hero_title", "mission_eyebrow", "tax_note", "values_eyebrow", "values_title",
             "story_eyebrow", "cta_title", "cta_btn1_label", "cta_btn1_link", "cta_btn2_label", "cta_btn2_link"]


@pytest.fixture(scope="module", autouse=True)
def backup():
    orig = db.settings.find_one({"key": "about"})
    yield
    if orig:
        db.settings.replace_one({"key": "about"}, orig, upsert=True)
    else:
        db.settings.delete_one({"key": "about"})


def base_payload():
    d = requests.get(f"{API}/about-content").json()
    d.pop("updated_at", None)
    d.pop("updated_by", None)
    return d


def put(p, cookies=ADMIN):
    return requests.put(f"{API}/admin/about-content", json=p, cookies=cookies, headers=XHR)


# Public GET returns all new keys
def test_public_get_has_all_fields():
    r = requests.get(f"{API}/about-content")
    assert r.status_code == 200
    d = r.json()
    for k in TEXT_KEYS + ["hero_image", "hero_subtitle", "mission_title", "mission_body", "mission_image", "values", "story_title", "story"]:
        assert k in d, k
    assert "_id" not in d and "key" not in d


# Auth required
def test_put_requires_admin():
    assert put(base_payload(), cookies={}).status_code in (401, 403)


# Save every text field + persistence
def test_save_all_text_fields_persist():
    p = base_payload()
    for k in TEXT_KEYS:
        p[k] = f"TEST_{k}"
    p["cta_btn1_link"] = "/donate"
    p["cta_btn2_link"] = "https://example.com/x"
    p["hero_image"] = "https://images.example.com/hero.jpg"
    p["story"][0]["image"] = "https://images.example.com/s.jpg"
    r = put(p)
    assert r.status_code == 200, r.text
    g = requests.get(f"{API}/about-content").json()
    for k in TEXT_KEYS:
        if k not in ("cta_btn1_link", "cta_btn2_link"):
            assert g[k] == f"TEST_{k}"
    assert g["cta_btn1_link"] == "/donate" and g["cta_btn2_link"] == "https://example.com/x"
    assert g["hero_image"] == "https://images.example.com/hero.jpg"
    assert g["story"][0]["image"] == "https://images.example.com/s.jpg"
    assert g["updated_at"]


# Link validation
@pytest.mark.parametrize("link", ["javascript:alert(1)", "//evil.com", "http://x.com", "ftp://a"])
def test_bad_links_rejected(link):
    p = base_payload()
    p["cta_btn1_link"] = link
    r = put(p)
    assert r.status_code == 400 and "Button links" in r.json()["detail"]


def test_mailto_link_ok():
    p = base_payload()
    p["cta_btn2_link"] = "mailto:hi@example.com"
    assert put(p).status_code == 200


# Image validation
def test_bad_hero_image_rejected():
    p = base_payload()
    p["hero_image"] = "http://insecure.com/a.jpg"
    assert put(p).status_code == 400


# Empty optional fields: UI promises "leave empty to hide" for tax_note and CTA button labels
def test_empty_tax_note_hides():
    p = base_payload()
    p["tax_note"] = ""
    put(p)
    assert requests.get(f"{API}/about-content").json()["tax_note"] == "", "tax_note empty should persist as '' (hide)"


def test_empty_cta_label_hides():
    p = base_payload()
    p["cta_btn1_label"] = ""
    put(p)
    assert requests.get(f"{API}/about-content").json()["cta_btn1_label"] == "", "empty cta label should persist as '' (hide)"


# Max length truncation
def test_length_truncation():
    p = base_payload()
    p["hero_kicker"] = "K" * 200
    p["cta_btn1_label"] = "L" * 100
    r = put(p)
    assert r.status_code == 200
    assert len(r.json()["hero_kicker"]) == 80 and len(r.json()["cta_btn1_label"]) == 40


# Existing validations still work
def test_values_and_mission_validation():
    p = base_payload()
    p["values"] = []
    assert put(p).status_code == 400
    p = base_payload()
    p["mission_body"] = "  "
    assert put(p).status_code == 400
