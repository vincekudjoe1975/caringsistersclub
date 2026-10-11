"""Seed data for iter32 frontend testing: 3 QA leaders, 2 QA photos tagged, 1 timed session."""
import os, sys, io, base64, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env'); load_dotenv('/app/frontend/.env')
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
C = {"session_token": "qa_tok_123"}
X = {"X-Requested-With": "XMLHttpRequest"}

def _png():
    return io.BytesIO(base64.b64decode(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="))

def up():
    # Leaders
    for i, (name, role, group) in enumerate([("QA Alice", "Director", "executive"), ("QA Beth", "Program Lead", "executive"), ("QA Carla", "Advisor", "board")]):
        r = requests.post(f"{BASE}/api/admin/leaders",
                          json={"name": name, "role": role, "group": group, "bio": f"Bio for {name}", "photo_url": "", "linkedin_url": "", "email": "", "order": i},
                          cookies=C, headers=X)
        print("leader:", r.status_code, name)
    # Photos tagged QA Night
    ids = []
    for i in range(2):
        f = {"file": (f"qa_{i}.png", _png(), "image/png")}
        d = {"category": "gallery", "title": f"QA Photo {i}"}
        r = requests.post(f"{BASE}/api/media", files=f, data=d, cookies=C, headers=X)
        mid = r.json()["id"]; ids.append(mid)
        requests.put(f"{BASE}/api/admin/gallery/{mid}",
                     json={"title": f"QA Photo {i}", "description": "", "tag_type": "event",
                           "tag_label": "QA Album Night", "tag_ref": "", "hidden": False, "album_key": ""},
                     cookies=C, headers=X)
        print("photo:", mid)
    # Session (future-dated, timed, with location)
    p = requests.get(f"{BASE}/api/programs/business-elevation-lab").json()
    r = requests.post(f"{BASE}/api/admin/programs/{p['id']}/sessions",
                      json={"date": "2026-12-05", "start_time": "18:30", "end_time": "20:00",
                            "location": "QA Hall", "seats": 10, "notes": "QA note"},
                      cookies=C, headers=X)
    print("session:", r.status_code, r.json().get("id"))

def down():
    db.leaders.delete_many({"name": {"$regex": "^QA "}})
    for m in db.media.find({"title": {"$regex": "^QA Photo"}}, {"id": 1}):
        requests.delete(f"{BASE}/api/admin/gallery/{m['id']}", cookies=C, headers=X)
    db.media.delete_many({"title": {"$regex": "^QA Photo"}})
    db.gallery_albums.delete_many({"$or": [{"title": {"$regex": "^QA"}}, {"key": "t:event:qa album night"}]})
    db.program_sessions.delete_many({"location": "QA Hall"})
    db.submissions.delete_many({"data.email": {"$regex": "^qa\\.person"}})
    db.session_reminders.delete_many({})
    print("cleaned")

if __name__ == "__main__":
    (up if sys.argv[1] == "up" else down)()
