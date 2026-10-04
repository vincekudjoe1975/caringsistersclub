# Caring Sisters Club — Product Requirements & Status

## Overview
Full-stack nonprofit website clone (React + FastAPI + MongoDB) for The Caring Sisters Club.
Public multi-page site + admin portal. Emergent-managed Google sign-in, object storage,
Stripe donations (claimable sandbox), managed email, donor administration, campaign tools.

## Architecture
- Frontend: React (`/app/frontend/src`), pages in `src/pages`, Tailwind, shadcn/ui.
- Backend: FastAPI single file `/app/backend/server.py`, all routes `/api` prefixed.
- DB: MongoDB (`MONGO_URL`, `DB_NAME=test_database`). Collections: users, user_sessions,
  settings, allowed_emails, submissions, payment_transactions, media, donor_notes,
  thankyou_sent, milestones_sent, reminders_sent, scheduled_runs.
- Auth: Emergent Google sign-in; first user = owner/admin, others pending until approved.
- Integrations: Stripe (sandbox), Emergent email (sandbox returns 422 — not delivering),
  Emergent object storage.

## Key donation flow
1. `POST /api/payments/checkout` → creates Stripe checkout + inserts `pending` payment_transaction.
2. User completes on Stripe → `/payment/success` polls `GET /api/payments/status/{id}` → flips to `paid`.
3. Admin → Donations reads only `payment_status=paid`; pending shown in separate section.

## Implemented (history)
- Visual clone, real leadership team photos + logo, admin media library.
- Form persistence (volunteer/membership/contact/RSVP) + admin inbox.
- Stripe one-time/monthly donations, donor wall, fundraising thermometer, campaign settings.
- Receipts, year-end statements, campaign progress emails, milestone emails, recurring reminders.
- Donor profiles (lifetime giving, history), CSV export, daily scheduler.

## Implemented 2026-10-04 (this session)
- **Donation display bug fixed**: root cause was an earlier sample-seed script running
  `delete_many({})` on payment_transactions, wiping real gifts. Removed 5 fake `sample_demo`
  rows, recovered the real $50 one-time donation from the surviving submissions copy.
- **Pending/Incomplete checkouts section** added to Admin → Donations (`pending_items` in
  `GET /api/admin/donations`). Backend tested, frontend additive.
- **Donor Notes & Tags**: `donor_notes` collection; `PUT /api/admin/donors/{email}/notes`;
  notes+tags surfaced in `GET /api/admin/donors` and `/admin/donors/{email}`; editor in
  AdminDonors modal. Tested (save/persist/return).
- **Lapsed Donor Alerts**: monthly donor flagged `lapsed` when last monthly gift > 35 days
  (grace period). `lapsed_count` + alert banner + "LAPSED" badges + lapsed-only filter in
  AdminDonors. Tested (40-day-old monthly flagged correctly).
- **Thank-You Automation**: configurable `thankyou_enabled/threshold/sender_name/note` in
  campaign settings; `_maybe_send_thankyou()` fires a personal board-member email on any
  newly-paid gift ≥ threshold (default $250), deduped via `thankyou_sent`. UI in AdminCampaign.
  Tested (threshold gating + dedup). Email send attempts but sandbox returns 422.
- **Admin Donations auto-refresh** (AdminDonations.jsx): silent re-fetch every 20s, re-fetch
  on tab/window focus + visibilitychange, manual "Refresh" button, and an "Updated HH:MM"
  timestamp. Verified 100% by automated tester (new paid donation appeared within ~16s with
  no page reload; summary cards updated).
- **Email delivery confirmed working**: the Emergent managed email uses a platform-verified
  sending domain (no Resend account/domain setup needed). The earlier HTTP 422 was the
  provider blocking fake `@example.com` test addresses ("Undeliverable recipient"); real
  recipient addresses return 202 + message id. Verified live.
- **Security hardening** (from audit): (a) SEC-003 fixed — public `GET /api/settings` now
  returns only public campaign fields; new admin-only `GET /api/admin/settings` returns the
  full config (AdminCampaign uses it). (b) SEC-002 CSRF — a `csrf_protect` middleware blocks
  mutating requests that carry a `session_token` cookie but lack `X-Requested-With:
  XMLHttpRequest`; the frontend axios instance (`lib/api.js`) sends this header on every call.
  Stripe webhook and public form posts (no cookie) are unaffected. Verified end-to-end.
- **Live Donation Feed** (AdminDonations.jsx): when auto-refresh brings in a new paid gift,
  the row flashes a gentle gold highlight (`.gift-row-new`, Sparkles icon) and a toast
  "🎉 A new gift just arrived!" fires. Verified 100% by automated tester.
- **Test Receipt** (admin-only `POST /api/admin/email/test-receipt`): sends the real branded
  receipt template to the logged-in admin's OWN email (G4-safe). Button in AdminCampaign →
  "Email Delivery Test". Real delivery confirmed (202) via the production send_email path.
- **Reactivation "We Miss You" email** (`POST /api/admin/donors/{email}/reactivation`,
  admin-only, CSRF-protected): one-click warm email to a lapsed donor; recipient must be an
  existing donor on record (404 otherwise, G4-safe). Button appears in the lapsed section of
  the AdminDonors profile modal. Template delivery confirmed (202).
- **Rate limiting**: gentle in-memory per-IP sliding-window limiter (`_rate_limit`) on public
  `POST /api/submissions` (5/60s) and `POST /api/payments/checkout` (6/300s); returns 429 with
  Retry-After. Verified (400×5 then 429).

## Known issues / notes
- **Email delivery works** via the Emergent platform-verified domain (202 + id for real
  addresses). It rejects obviously-fake recipients like `@example.com` with HTTP 422
  ("Undeliverable recipient") — expected, not a bug. `send_email` swallows failures (logs,
  returns None) so a bad address never breaks checkout or a bulk loop.
- **Stripe is sandbox/claimable** — Donate does not accept real cards until onboarding/Go-Live.
- CSRF is enforced via `X-Requested-With` header on cookie-auth mutations; any future
  non-axios client must send this header.
- Scheduler runtime persistence over long periods unverified.
- Never run destructive seed/cleanup on `payment_transactions` without preserving real data.

## Backlog / next (P1)
- Stripe Go-Live guidance + production credential configuration (user action).
- Optional: cross-check lapsed status against live Stripe subscription status.
- Optional security hardening (P3 from audit): rate-limit public POSTs, upload size cap,
  `X-Content-Type-Options: nosniff` on served media.
- User still to confirm a fresh monthly donation lands in the DB after full Stripe completion
  (on the SAME environment they view the admin — preview vs deployed use separate DBs).
