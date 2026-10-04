#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================


#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Clone of caringsistersclub.org made grant-compliant. Added Emergent Google sign-in (auth)
  and file & media storage (Emergent object storage) with a protected admin dashboard to
  manage gallery photos, leadership photos, event images, and PDF documents.

backend:
  - task: "Emergent Google Auth - session exchange, /auth/me, logout"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/auth/session exchanges session_id via Emergent, stores session_token in user_sessions with 7-day expiry, sets httpOnly cookie, upserts user (role admin). GET /api/auth/me returns current user via cookie or Bearer. POST /api/auth/logout clears session. Cannot fully test session exchange without a real session_id; please test unauthenticated 401 behavior on /auth/me and /media (POST/DELETE), and that a seeded user_sessions token authenticates /auth/me (see auth_testing.md pattern)."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL AUTH TESTS PASSED (3/3). Tested via /app/backend_test.py with seeded MongoDB user/session per auth_testing.md pattern. Results: (1) GET /api/auth/me returns 401 when unauthenticated ✅ (2) GET /api/auth/me with Bearer token returns correct user (email, name, role=admin) ✅ (3) POST /api/auth/logout succeeds (200) ✅. Auth dependency works correctly for protected endpoints. Session token authentication via Bearer header and cookie both functional."
  - task: "File & media storage via Emergent object storage"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/media (multipart: file, category, title, subtitle) is auth-protected, uploads to Emergent object storage (init_storage succeeded at startup per logs), stores metadata in db.media with is_deleted flag. GET /api/media?category=... is public list. GET /api/media/file/{id} serves bytes publicly. DELETE /api/media/{id} soft-deletes (auth). Categories: gallery, board, event, document. Please test: unauthenticated POST/DELETE return 401; with a seeded session token, upload a small image + a PDF, list them, fetch the file bytes (200 + correct content-type), soft-delete removes it from list."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL MEDIA TESTS PASSED (12/12). Tested via /app/backend_test.py with authenticated Bearer token. Results: (1) POST /api/media without auth returns 401 ✅ (2) Upload PNG to gallery category succeeds, returns id/url/storage_path/size ✅ (3) Upload PDF to document category with title='Form 990 2024' and subtitle='2024' succeeds ✅ (4) Invalid category returns 400 ✅ (5) GET /api/media?category=gallery lists uploaded image ✅ (6) GET /api/media?category=document lists uploaded PDF ✅ (7) GET /api/media/file/{id} returns image with Content-Type: image/png and non-empty body ✅ (8) GET /api/media/file/{id} returns PDF with Content-Type: application/pdf and non-empty body ✅ (9) DELETE /api/media/{id} without auth returns 401 ✅ (10) DELETE /api/media/{id} with auth soft-deletes (200) ✅ (11) Soft-deleted item excluded from subsequent list ✅ (12) GET /api/media/file/{id} for deleted item returns 404 ✅. Emergent object storage integration working correctly."

  - task: "Form submissions - public create, admin list/counts/read/delete"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/submissions is PUBLIC, accepts {type, ...fields}; type must be volunteer|member|contact|rsvp|donation (invalid -> 400). Stores {id, type, data, read:false, created_at} in db.submissions. GET /api/submissions?type= (auth), GET /api/submissions/counts (auth) returns per-type {total, unread}, PATCH /api/submissions/{id}/read (auth), DELETE /api/submissions/{id} (auth). Please test: public create for each valid type + 400 invalid; unauthenticated GET/PATCH/DELETE return 401; with seeded Bearer token: list returns created items, counts reflect totals/unread, marking read decrements unread, delete removes item."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL FORM SUBMISSION TESTS PASSED (14/14). Tested via /app/backend_test.py with seeded MongoDB user/session per auth_testing.md pattern. Results: (1) POST /api/submissions for each valid type (volunteer, member, contact, rsvp, donation) returns 200 with id ✅ (2) POST /api/submissions with invalid type 'spam' returns 400 ✅ (3) GET /api/submissions without auth returns 401 ✅ (4) GET /api/submissions/counts without auth returns 401 ✅ (5) PATCH /api/submissions/{id}/read without auth returns 401 ✅ (6) DELETE /api/submissions/{id} without auth returns 401 ✅ (7) GET /api/submissions?type=volunteer with Bearer token returns created submission ✅ (8) GET /api/submissions/counts with Bearer token returns correct structure with total/unread for all types ✅ (9) PATCH /api/submissions/{id}/read with Bearer token decrements unread count (1->0) ✅ (10) DELETE /api/submissions/{id} with Bearer token removes item from list and decrements total count ✅. All endpoints working correctly. Test data cleaned up from MongoDB."

frontend:
  - task: "Auth context + admin dashboard + public content wiring"
    implemented: true
    working: "NA"
    file: "frontend/src/pages/Admin.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Frontend not yet tested by automation; will ask user before frontend testing."

  - task: "Stripe donations - checkout, status polling, webhook"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Flow A claimable sandbox. POST /api/payments/checkout {amount, frequency(one-time|monthly), donor_name?, donor_email?, origin_url} returns {checkout_url, session_id}; inserts payment_transactions (initiated/pending). GET /api/payments/status/{session_id} public, with inline Stripe retrieve fallback to flip paid + record donation submission. POST /api/stripe/webhook. stripe==14.4.1, keys in backend/.env. Needs testing."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL STRIPE PAYMENT TESTS PASSED (6/6). Tested via /app/backend_test.py. Results: (1) POST /api/payments/checkout with one-time donation (amount=50) returns 200 with valid checkout_url (contains stripe.com) and session_id (starts with cs_) ✅ (2) Payment transaction inserted in MongoDB with status='initiated' and payment_status='pending' ✅ (3) POST /api/payments/checkout with monthly subscription (amount=25) returns 200 with valid checkout_url and session_id (subscription mode) ✅ (4) POST /api/payments/checkout with amount below minimum (0.5) returns 400 with 'Invalid donation amount' ✅ (5) POST /api/payments/checkout with amount above maximum (200000) returns 400 with 'Invalid donation amount' ✅ (6) GET /api/payments/status/{session_id} for valid session returns 200 with payment_status='pending' (not paid, as expected) ✅ (7) GET /api/payments/status/nonexistent_session returns 404 ✅. Stripe API integration working correctly (stripe==14.4.1, STRIPE_SECRET_KEY configured). Backend logs confirm successful Stripe API calls (response_code=200). Test payment_transactions cleaned up from MongoDB."
        -working: true
        -agent: "testing"
        -comment: "✅ REGRESSION TEST PASSED (5/5) after refactor. Tested via /app/regression_test.py using public URL. Results: (1) POST /api/payments/checkout with one-time donation (amount=50) returns 200 with valid checkout_url (https://checkout.stripe.com) and session_id (cs_test_...) ✅ (2) POST /api/payments/checkout with monthly subscription (amount=25) returns 200 with valid checkout_url and session_id ✅ (3) Amount validation working: amount=0.5 returns 400 with 'Invalid donation amount' ✅ (4) Amount validation working: amount=200000 returns 400 with 'Invalid donation amount' ✅ (5) GET /api/payments/status/{session_id} returns 200 with payment_status='pending' ✅ (6) GET /api/media?category=gallery (public) returns 200 with empty list [] ✅. All test payment_transactions cleaned up from MongoDB. Stripe payment endpoints working correctly after refactor."

  - task: "Admin allowlist (role-based) + team management"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Added role-based access control with require_admin dependency. GET /api/admin/team returns {users, allowed_emails, me}. POST /api/admin/team/allow {email} adds to allowlist. POST /api/admin/team/{user_id}/role {role} updates role (400 if removing own admin). POST /api/admin/team/revoke-email {email} removes from allowlist. All admin endpoints (submissions, media upload, admin/donations, admin/team) now require role='admin', return 403 for role='pending'."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL ROLE ENFORCEMENT & TEAM MANAGEMENT TESTS PASSED (14/14). Tested via /app/backend_test_new_features.py with seeded admin and pending users. ROLE ENFORCEMENT (9/9): (1) GET /api/submissions with pending role returns 403 ✅ (2) GET /api/submissions with admin role returns 200 ✅ (3) GET /api/submissions/counts with pending role returns 403 ✅ (4) GET /api/submissions/counts with admin role returns 200 ✅ (5) GET /api/admin/donations with pending role returns 403 ✅ (6) GET /api/admin/donations with admin role returns 200 ✅ (7) GET /api/admin/team with pending role returns 403 ✅ (8) GET /api/admin/team with admin role returns 200 ✅ (9) POST /api/media with pending role returns 403 ✅. TEAM MANAGEMENT (5/5): (1) GET /api/admin/team returns {users, allowed_emails, me} with correct structure ✅ (2) POST /api/admin/team/allow adds 'newperson@example.com' to allowlist ✅ (3) POST /api/admin/team/{self_user_id}/role with role='pending' returns 400 (cannot remove own admin) ✅ (4) POST /api/admin/team/{other_user_id}/role updates role to admin ✅ (5) POST /api/admin/team/revoke-email removes email from allowlist ✅. All test data cleaned up from MongoDB."

  - task: "Donor wall public + admin donations"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /api/donations/public (PUBLIC) returns {total_raised, goal=50000, donor_count, recent[]} with name anonymization (anonymous:true -> 'Anonymous', else 'FirstName LastInitial.'). GET /api/admin/donations (admin) returns {items, summary{total_raised, count, monthly_count, onetime_count}}. Supports ?frequency=monthly|one-time filter."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL DONOR WALL & ADMIN DONATIONS TESTS PASSED (5/5). Tested via /app/backend_test_new_features.py with seeded paid payment_transactions. DONOR WALL (2/2): (1) GET /api/donations/public returns correct structure {total_raised: $175, goal: $50000, donor_count: 3, recent: [...]} ✅ (2) Name anonymization working: Jane Doe (anonymous:false) displays as 'Jane D.', Secret Giver (anonymous:true) displays as 'Anonymous' ✅. ADMIN DONATIONS (3/3): (1) GET /api/admin/donations returns {items, summary} with correct totals (total_raised: $175, count: 3, monthly_count: 1, onetime_count: 2) ✅ (2) GET /api/admin/donations?frequency=monthly filters to only monthly donations (1 found) ✅ (3) GET /api/admin/donations?frequency=one-time filters to only one-time donations (2 found) ✅. All test data cleaned up from MongoDB."

  - task: "Campaign settings (editable goal/title)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Added campaign settings endpoints. GET /api/settings (PUBLIC) returns {campaign_title, campaign_subtitle, goal} with default goal=50000. PUT /api/admin/settings (admin-only) updates settings with validation (goal must be > 0). Settings stored in db.settings with key='site'. GET /api/donations/public now includes campaign_title and campaign_subtitle from settings."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL CAMPAIGN SETTINGS TESTS PASSED (11/11). Tested via /app/backend_test_campaign_settings.py with seeded admin (role='admin') and pending (role='pending') users per auth_testing.md pattern. CAMPAIGN SETTINGS (7/7): (1) GET /api/settings (PUBLIC) returns 200 with default goal=50000, campaign_title, campaign_subtitle ✅ (2) PUT /api/admin/settings without auth returns 401 ✅ (3) PUT /api/admin/settings with role='pending' user returns 403 ✅ (4) PUT /api/admin/settings with admin token and body {campaign_title:'Build the Center', campaign_subtitle:'Capital Campaign', goal:75000} returns 200 with updated values ✅ (5) PUT /api/admin/settings with negative goal (-5) returns 400 ✅ (6) GET /api/settings reflects new values (goal=75000, campaign_title='Build the Center', campaign_subtitle='Capital Campaign') ✅ (7) GET /api/donations/public includes new goal=75000, campaign_title='Build the Center', campaign_subtitle='Capital Campaign' ✅. WEBHOOK SIGNATURE (2/2): (8) POST /api/stripe/webhook with no stripe-signature header returns 400 (not 500, signature verification active) ✅ (9) POST /api/stripe/webhook with invalid stripe-signature header returns 400 (not 500) ✅. LIGHT REGRESSION (2/2): (10) POST /api/payments/checkout with amount=40, frequency='one-time', origin_url='https://example.com' returns 200 with checkout_url (contains stripe.com) and session_id (cs_test_...) ✅ (11) GET /api/donations/public returns 200 with correct structure {total_raised, goal, donor_count, recent} ✅. All test data cleaned up from MongoDB (users, user_sessions, settings, payment_transactions)."

  - task: "Campaign deadline setting"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Added deadline field to campaign settings. PUT /api/admin/settings accepts deadline (ISO date YYYY-MM-DD) or empty string to clear. GET /api/settings and GET /api/donations/public both return deadline field."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL DEADLINE TESTS PASSED (5/5). Tested via /app/backend_test_deadline_recurring.py with seeded admin user (role='admin') per auth_testing.md pattern. Results: (1) PUT /api/admin/settings with deadline='2026-12-31' returns 200 with deadline='2026-12-31' ✅ (2) GET /api/settings includes deadline='2026-12-31' ✅ (3) GET /api/donations/public includes deadline='2026-12-31' ✅ (4) PUT /api/admin/settings with deadline='' (empty string) clears deadline, returns 200 with deadline=None ✅ (5) GET /api/settings shows deadline=None after clearing ✅. All test data cleaned up from MongoDB (users, user_sessions, settings, payment_transactions, milestones_sent)."

  - task: "Recurring donation metrics (active_recurring, monthly_revenue)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Enhanced GET /api/admin/donations summary to include active_recurring (count of unique stripe_subscription_id values) and monthly_revenue (sum of ONE gift per active subscription, not counting multiple renewals). Logic: groups monthly paid transactions by stripe_subscription_id, counts unique subscriptions, and sums one amount per subscription."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL RECURRING METRICS TESTS PASSED (1/1). Tested via /app/backend_test_deadline_recurring.py with seeded payment_transactions. Seeded 3 paid transactions: (a) monthly amount=25 with stripe_subscription_id='sub_A', (b) monthly amount=25 with stripe_subscription_id='sub_A' and is_renewal=true, (c) one-time amount=100. GET /api/admin/donations summary verified: total_raised=150 ✅, monthly_count=2 ✅, onetime_count=1 ✅, active_recurring=1 (unique subscription sub_A) ✅, monthly_revenue=25 (ONE gift per subscription, not both renewals) ✅. All test data cleaned up from MongoDB."

  - task: "Milestone emails (no 500 errors)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Added _check_milestones function that sends email alerts to admins when fundraising reaches 25%, 50%, or 100% of goal. Stores sent milestones in db.milestones_sent to avoid duplicates. Milestone logic runs on paid-donation recording (webhook/status polling), which can't be triggered headlessly in tests."
        -working: true
        -agent: "testing"
        -comment: "✅ ALL NO-500 / MILESTONE TESTS PASSED (4/4). Tested via /app/backend_test_deadline_recurring.py. Results: (1) PUT /api/admin/settings with goal=100 returns 200 ✅ (2) Seeded paid one-time donation amount=60 (60% of goal) ✅ (3) GET /api/donations/public returns 200 (no 500 error) with total_raised=210, goal=100 ✅ (4) GET /api/admin/donations returns 200 (no 500 error) with summary.total_raised=210 ✅. Note: Milestone emails fire only on live paid-donation recording which can't be triggered headlessly. Endpoints are healthy and db.milestones_sent collection is writable. All test data cleaned up from MongoDB."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 8
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: "New features to test (backend/server.py). Seed Bearer token per /app/auth_testing.md but NOTE new role model: require_admin needs role=='admin'. Seed the test user with role:'admin'. Tests: (1) ALLOWLIST/ROLE: media upload/delete, submissions list/counts/read/delete, /admin/donations, /admin/team require role admin -> a role:'pending' seeded user gets 403; role:'admin' gets 200. (2) TEAM: GET /api/admin/team -> {users, allowed_emails, me}; POST /api/admin/team/allow {email} 200 adds allowlist; POST /api/admin/team/{user_id}/role {role} updates and MUST 400 if setting your OWN user_id to 'pending'; POST /api/admin/team/revoke-email {email} removes. (3) DONOR WALL: GET /api/donations/public is PUBLIC -> {total_raised, goal=50000, donor_count, recent[]}; seed 2 payment_transactions payment_status:'paid' (one anonymous:true named, one anonymous:false donor_name 'Jane Doe') and verify anonymous shows 'Anonymous', other shows 'Jane D.', totals correct. (4) ADMIN DONATIONS: GET /api/admin/donations (admin) -> {items, summary{total_raised,count,monthly_count,onetime_count}}; ?frequency=monthly filters. (5) EMAIL best-effort: no real delivery needed; ensure no 500s. Clean up seeded data."

agent_communication:
    -agent: "main"
    -message: "Please test the new backend auth + media endpoints. Read /app/auth_testing.md for the Emergent auth session-seeding pattern (insert a user with a custom user_id and a matching user_sessions doc with session_token + future expires_at, then use Authorization: Bearer <session_token>). Object storage init succeeded at startup. Focus: 401 on protected endpoints when unauthenticated; full media lifecycle (upload image + PDF, list, fetch file bytes with correct content-type, soft-delete) when authenticated. DB name is in backend/.env (DB_NAME). Do NOT edit the Testing Protocol block."
    -agent: "testing"
    -message: "✅ Backend testing complete. All 15 tests passed (100% success rate). Created /app/backend_test.py with comprehensive test suite covering both Emergent Google Auth and File/Media Storage features. Auth: All endpoints working correctly (401 for unauthenticated, Bearer token auth, logout). Media: Full lifecycle tested (upload image/PDF, list by category, fetch file bytes with correct Content-Type, soft-delete, 401 for protected endpoints). Emergent object storage integration confirmed working. Test data cleaned up from MongoDB. Both backend tasks marked as working: true. Ready for main agent to summarize and finish."

agent_communication:
    -agent: "testing"
    -message: "✅ Form submissions testing complete. All 14 tests passed (100% success rate). Extended /app/backend_test.py to include comprehensive form submission tests. Results: (1) Public POST /api/submissions works for all 5 valid types (volunteer, member, contact, rsvp, donation), each returns 200 with id. (2) Invalid type 'spam' correctly returns 400. (3) All protected endpoints (GET /api/submissions, GET /api/submissions/counts, PATCH /api/submissions/{id}/read, DELETE /api/submissions/{id}) return 401 when unauthenticated. (4) With Bearer token authentication: list by type works correctly, counts endpoint returns proper structure with total/unread for all types, mark-as-read decrements unread count, delete removes item and decrements total. All test data cleaned up from MongoDB. Task marked as working: true. All backend features now fully tested and working."

agent_communication:
    -agent: "testing"
    -message: "✅ Stripe payment testing complete. All 6 tests passed (100% success rate). Extended /app/backend_test.py to include comprehensive Stripe payment tests. Results: (1) POST /api/payments/checkout with one-time donation (amount=50, donor_name='Test Donor', donor_email='test@example.com') returns 200 with valid checkout_url (contains 'stripe.com') and session_id (starts with 'cs_'). (2) Payment transaction correctly inserted in MongoDB with status='initiated' and payment_status='pending'. (3) POST /api/payments/checkout with monthly subscription (amount=25) returns 200 with valid checkout_url and session_id in subscription mode. (4) Amount validation working: amount below minimum (0.5) returns 400 with 'Invalid donation amount'. (5) Amount above maximum (200000) returns 400 with 'Invalid donation amount'. (6) GET /api/payments/status/{session_id} for valid session returns 200 with payment_status='pending' (not paid, as expected since no card payment completed). (7) GET /api/payments/status/nonexistent_session returns 404. Stripe API integration confirmed working (stripe==14.4.1, STRIPE_SECRET_KEY configured in backend/.env). Backend logs show successful Stripe API calls (response_code=200). Test payment_transactions cleaned up from MongoDB. Task marked as working: true. All backend features fully tested and working."

agent_communication:
    -agent: "testing"
    -message: "✅ Regression test complete after refactor. All 5 tests passed (100% success rate). Created /app/regression_test.py for quick regression verification. Tested using public URL (https://caring-sisters-clone.preview.emergentagent.com/api). Results: (1) POST /api/payments/checkout with one-time donation (amount=50) returns 200 with valid Stripe checkout URL and session_id (cs_test_...) ✅ (2) POST /api/payments/checkout with monthly subscription (amount=25) returns 200 with valid checkout URL and session_id ✅ (3) Amount validation: amount=0.5 returns 400 with 'Invalid donation amount' ✅ (4) Amount validation: amount=200000 returns 400 with 'Invalid donation amount' ✅ (5) GET /api/payments/status/{session_id} returns 200 with payment_status='pending' ✅ (6) GET /api/media?category=gallery (public) returns 200 with empty list [] ✅. Test payment_transactions cleaned up from MongoDB. Stripe payment endpoints working correctly after refactor. No issues found."

agent_communication:
    -agent: "testing"
    -message: "✅ NEW FEATURES TESTING COMPLETE. All 19 tests passed (100% success rate). Created /app/backend_test_new_features.py to test role enforcement, team management, donor wall, and admin donations. ROLE ENFORCEMENT (9/9 passed): All admin-protected endpoints (GET /api/submissions, GET /api/submissions/counts, GET /api/admin/donations, GET /api/admin/team, POST /api/media) correctly return 403 for role='pending' users and 200 for role='admin' users. TEAM MANAGEMENT (5/5 passed): GET /api/admin/team returns {users, allowed_emails, me}. POST /api/admin/team/allow adds email to allowlist. POST /api/admin/team/{user_id}/role updates role but returns 400 when trying to remove own admin access. POST /api/admin/team/revoke-email removes email from allowlist. DONOR WALL (2/2 passed): GET /api/donations/public (PUBLIC, no auth) returns {total_raised, goal=50000, donor_count, recent[]} with correct anonymization (anonymous:true -> 'Anonymous', anonymous:false -> 'FirstName LastInitial.'). ADMIN DONATIONS (3/3 passed): GET /api/admin/donations returns {items, summary{total_raised, count, monthly_count, onetime_count}}. Frequency filters (?frequency=monthly|one-time) work correctly. All test data cleaned up from MongoDB (users, user_sessions, payment_transactions, allowed_emails). No 500 errors encountered. All backend features fully tested and working."

agent_communication:
    -agent: "main"
    -message: "Test newly added backend features in backend/server.py. Seed an admin Bearer token per /app/auth_testing.md (set role:'admin' on the seeded user). Do NOT edit the Testing Protocol block. Backend base http://localhost:8001, routes prefixed /api. 1) CAMPAIGN SETTINGS: GET /api/settings is PUBLIC -> 200 with {campaign_title, campaign_subtitle, goal}; default goal should be 50000 if never set. PUT /api/admin/settings requires admin: without auth -> 401; with a role:'pending' user token -> 403; with admin token and body {'campaign_title':'Build the Center','campaign_subtitle':'Capital Campaign','goal':75000} -> 200 returning the updated values. PUT /api/admin/settings with {'goal': -5} (admin) -> 400. After the successful update, GET /api/settings -> reflects new title/subtitle/goal; GET /api/donations/public -> goal==75000 and includes campaign_title=='Build the Center', campaign_subtitle=='Capital Campaign'. 2) WEBHOOK SIGNATURE: POST /api/stripe/webhook with an arbitrary JSON body and no/invalid 'stripe-signature' header -> 400 (signature verification active). Confirm it does NOT 500. 3) LIGHT REGRESSION: POST /api/payments/checkout {'amount':40,'frequency':'one-time','origin_url':'https://example.com'} -> 200 with checkout_url + session_id. GET /api/donations/public -> 200. Report pass/fail per check and update test_result.md status_history. Clean up: reset/delete the settings doc (db.settings) you created and any seeded users/sessions/payment_transactions."
    -agent: "testing"
    -message: "✅ CAMPAIGN SETTINGS, WEBHOOK SIGNATURE & LIGHT REGRESSION TESTING COMPLETE. All 11 tests passed (100% success rate). Created /app/backend_test_campaign_settings.py with comprehensive test suite. Seeded admin user (role='admin') and pending user (role='pending') per auth_testing.md pattern. CAMPAIGN SETTINGS (7/7 passed): (1) GET /api/settings (PUBLIC) returns 200 with default goal=50000, campaign_title, campaign_subtitle ✅ (2) PUT /api/admin/settings without auth returns 401 ✅ (3) PUT /api/admin/settings with role='pending' user returns 403 ✅ (4) PUT /api/admin/settings with admin token and body {campaign_title:'Build the Center', campaign_subtitle:'Capital Campaign', goal:75000} returns 200 with updated values ✅ (5) PUT /api/admin/settings with negative goal (-5) returns 400 ✅ (6) GET /api/settings reflects new values (goal=75000, campaign_title='Build the Center', campaign_subtitle='Capital Campaign') ✅ (7) GET /api/donations/public includes new goal=75000, campaign_title='Build the Center', campaign_subtitle='Capital Campaign' ✅. WEBHOOK SIGNATURE (2/2 passed): (8) POST /api/stripe/webhook with no stripe-signature header returns 400 (not 500, signature verification active) ✅ (9) POST /api/stripe/webhook with invalid stripe-signature header returns 400 (not 500) ✅. LIGHT REGRESSION (2/2 passed): (10) POST /api/payments/checkout with amount=40, frequency='one-time', origin_url='https://example.com' returns 200 with checkout_url (contains stripe.com) and session_id (cs_test_...) ✅ (11) GET /api/donations/public returns 200 with correct structure {total_raised, goal, donor_count, recent} ✅. All test data cleaned up from MongoDB (users, user_sessions, settings, payment_transactions). No issues found. All backend features fully tested and working."

agent_communication:
    -agent: "main"
    -message: "Test NEW backend additions (backend/server.py). Seed admin Bearer token per /app/auth_testing.md (role:'admin'). (1) DEADLINE SETTING: PUT /api/admin/settings {deadline:'2026-12-31'} (admin) -> 200; GET /api/settings and GET /api/donations/public both include deadline=='2026-12-31'. PUT with deadline:'' clears it (deadline null). (2) RECURRING METRICS: Seed 3 payment_transactions payment_status:'paid': two monthly (amount 25 with stripe_subscription_id 'sub_A'; amount 25 renewal with same stripe_subscription_id 'sub_A' + is_renewal:true) and one one-time amount 100. GET /api/admin/donations (admin) summary should include active_recurring (unique subscription count == 1 for sub_A) and monthly_revenue (== 25, counting ONE gift per active subscription, not both renewals). Verify total_raised==150, monthly_count==2, onetime_count==1. (3) MILESTONE EMAILS: set goal via PUT to 100; seed paid donations summing >=50 (e.g., a 60 one-time). Call GET /api/donations/public then trigger _check_milestones indirectly is hard; instead just verify no 500s and that db.milestones_sent can be written (milestone logic runs on paid-donation recording, which can't be triggered headlessly). Best-effort: confirm endpoints don't error. Clean up seeded data (payment_transactions, settings, milestones_sent, users, user_sessions)."
    -agent: "testing"
    -message: "✅ ALL NEW BACKEND FEATURES TESTED (10/10 tests passed). Created /app/backend_test_deadline_recurring.py with comprehensive test suite. Seeded admin user (role='admin') per auth_testing.md pattern. CAMPAIGN DEADLINE (5/5 passed): (1) PUT /api/admin/settings with deadline='2026-12-31' returns 200 with deadline='2026-12-31' ✅ (2) GET /api/settings includes deadline='2026-12-31' ✅ (3) GET /api/donations/public includes deadline='2026-12-31' ✅ (4) PUT /api/admin/settings with deadline='' clears deadline (returns None) ✅ (5) GET /api/settings shows deadline=None after clearing ✅. RECURRING METRICS (1/1 passed): Seeded 3 paid transactions (2 monthly with same stripe_subscription_id='sub_A', one with is_renewal=true; 1 one-time). GET /api/admin/donations summary verified: total_raised=150 ✅, monthly_count=2 ✅, onetime_count=1 ✅, active_recurring=1 (unique subscription) ✅, monthly_revenue=25 (ONE gift per subscription, not both renewals) ✅. NO-500 / MILESTONES (4/4 passed): (1) PUT /api/admin/settings with goal=100 returns 200 ✅ (2) Seeded paid one-time donation amount=60 ✅ (3) GET /api/donations/public returns 200 (no 500) ✅ (4) GET /api/admin/donations returns 200 (no 500) ✅. Note: Milestone emails fire only on live paid-donation recording which can't be triggered headlessly. Endpoints are healthy. All test data cleaned up from MongoDB (users, user_sessions, settings, payment_transactions, milestones_sent). All backend features fully tested and working."