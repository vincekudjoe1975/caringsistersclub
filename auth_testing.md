# Auth-Gated App Testing Playbook (Emergent Google Auth)

Backend runs on localhost:8001. All API routes are prefixed with `/api`.
DB name is set in `backend/.env` as `DB_NAME` (currently `test_database`).

## Step 1: Create Test User & Session (seed directly in MongoDB)
Emergent Google Auth cannot be completed headlessly (no real session_id), so seed a
session directly. The backend `get_current_user` reads `session_token` from the
`user_sessions` collection and matches it to a `users` doc by `user_id`.

```
mongosh --eval "
use('test_database');
var userId = 'user_test' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.admin.' + Date.now() + '@example.com',
  name: 'Test Admin',
  picture: 'https://via.placeholder.com/150',
  role: 'admin',
  created_at: new Date().toISOString()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
  created_at: new Date().toISOString()
});
print('SESSION_TOKEN=' + sessionToken);
"
```

## Step 2: Backend API Tests

Unauthenticated should be 401:
```
curl -i http://localhost:8001/api/auth/me
curl -i -X POST http://localhost:8001/api/media -F 'category=gallery' -F 'file=@/tmp/x.png'
```

Authenticated (use the seeded SESSION_TOKEN via Bearer header):
```
curl http://localhost:8001/api/auth/me -H "Authorization: Bearer <SESSION_TOKEN>"

# Upload an image
curl -X POST http://localhost:8001/api/media \
  -H "Authorization: Bearer <SESSION_TOKEN>" \
  -F 'category=gallery' -F 'title=Test Photo' -F 'file=@/tmp/test.png'

# Upload a PDF
curl -X POST http://localhost:8001/api/media \
  -H "Authorization: Bearer <SESSION_TOKEN>" \
  -F 'category=document' -F 'title=Form 990 2024' -F 'subtitle=2024' -F 'file=@/tmp/test.pdf'

# List (public)
curl http://localhost:8001/api/media?category=gallery

# Fetch file bytes (public) - check 200 + Content-Type header
curl -i http://localhost:8001/api/media/file/<ITEM_ID>

# Soft-delete (auth)
curl -X DELETE http://localhost:8001/api/media/<ITEM_ID> -H "Authorization: Bearer <SESSION_TOKEN>"
# then list again - item should be gone
```

## Success Indicators
- /api/auth/me returns the seeded user when Bearer token provided; 401 without.
- Upload returns JSON with id, url, storage_path, size.
- List returns uploaded items (excludes soft-deleted).
- File fetch returns 200 with correct Content-Type (image/png or application/pdf).
- Protected POST/DELETE return 401 unauthenticated.

## Cleanup
```
mongosh --eval "use('test_database'); db.users.deleteMany({email:/test\\.admin\\./}); db.user_sessions.deleteMany({session_token:/test_session/}); db.media.deleteMany({uploaded_by:/test\\.admin\\./});"
```
