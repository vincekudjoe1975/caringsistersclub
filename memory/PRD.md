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
- **Live test receipt** sent to caringsistersclub@gmail.com (202 delivered) to confirm
  donor-facing email in a real inbox.
- **Reactivation log**: `admin_donor_detail` now returns `reactivation_last_sent` (from the
  `reactivation_sent` collection); AdminDonors shows "Last 'we miss you' email sent <date>" in
  the lapsed block and the confirm dialog warns before a duplicate send. Verified.
- **Upload hardening** (P3 audit): `POST /api/media` enforces a 10 MB cap (413), an extension
  allowlist (images for gallery/board/event, PDF for document → 400 otherwise), and derives a
  safe content-type from the extension (never trusts client). `GET /api/media/file/{id}` now
  serves with `X-Content-Type-Options: nosniff` + `Content-Disposition: inline`. Verified.
- **Receipt branding**: new public `GET /api/brand/logo` serves `backend/brand_logo.png`;
  receipt/thank-you/reactivation emails show the logo (via `PUBLIC_APP_URL`) and receipts show
  a configurable real EIN (`org_ein` setting; fake "sample" EIN removed). EIN editable in
  AdminCampaign → Receipts & Compliance. Verified.
- **Lapsed auto-email**: `_send_lapsed_reactivations()` runs in the daily scheduler — auto-sends
  the "we miss you" email to lapsed monthly donors, gated by `lapsed_autoemail_enabled` and a
  `lapsed_cooldown_days` (default 30) cooldown via the `reactivation_sent` log. Toggle +
  cooldown in AdminCampaign. Verified (sends once, cooldown skips repeat, disable skips).
- **Go Live guidance** provided (Manage → Payments → Claim Stripe sandbox + install Emergent
  app; keys/webhook auto-managed). User action — not a code change.
- **Year-end statements branded**: `_year_statement_html` now uses the shared `_brand_header`
  (logo) and shows the configurable real EIN (fake "sample" EIN removed); `_run_year_statements`
  passes `org_ein` from settings. Verified.
- **Donor search filters + sortable columns** (AdminDonors.jsx): quick-filter chips with live
  counts — All / Monthly / Lapsed / Major ($500+) — plus clickable, sortable column headers
  (Donor, Gifts, Last Gift, Lifetime) via a `SortTh` component. Verified visually (Major filter
  shows only the $600 lapsed donor; name sort orders A→Z).
- **CSV by filter**: "Export CSV" button on the Donors tab downloads the currently-filtered +
  sorted donor list client-side (name, email, gifts, lifetime, last gift, monthly, lapsed, tags).
- **Donor segment email**: `POST /api/admin/donors/segment-email` + `GET
  /admin/donors/segment-count/{segment}` (admin-only, CSRF-protected). Sends a branded appeal
  (admin subject+message, escaped) to a server-computed segment (all/monthly/lapsed/major);
  compose modal in AdminDonors with live recipient count. Verified (count, send+deliver,
  400 on empty subject, 403 without CSRF header).
- **Segment email test copy**: `POST /api/admin/donors/segment-email/test` sends a preview of
  the appeal to the logged-in admin's own inbox ("[Test] …" subject); button in the compose
  modal. Verified (sent to own email, 400 on empty subject).
- **Appeal history**: `GET /api/admin/appeals` lists past segment appeals (segment, subject,
  sender name, sent/recipients counts, date) from the `segment_emails` collection; collapsible
  panel on the Donors tab. Note: email *open* tracking is not available via the managed email
  provider, so history shows delivered/sent counts only. Route placed at `/admin/appeals` to
  avoid shadowing `/admin/donors/{email}`. Verified.
- **Appeal templates**: `appeal_templates` collection + CRUD (`GET/POST /api/admin/appeal-templates`,
  `DELETE /api/admin/appeal-templates/{id}`). Compose modal shows saved templates as clickable
  chips (apply/delete) and a "Save as template" action. Verified.
- **Scheduled appeals**: `scheduled_appeals` collection + `GET/POST /api/admin/scheduled-appeals`,
  `DELETE /api/admin/scheduled-appeals/{id}` (cancel). Compose modal has a date picker that
  switches the primary button to "Schedule"; the daily scheduler (`_run_scheduled_appeals`)
  dispatches due appeals via the shared `_dispatch_segment_appeal` helper and logs them to
  appeal history. Scheduled Appeals panel on the Donors tab shows status + cancel. Verified
  (past-date 400, not-due→0, due→sent with counts, cancel-after-sent 404).

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

## 2026 — Recurring Appeals + Appeal Analytics (iteration_3: 100% pass)
- Scheduled appeals accept `repeat` (none|monthly|quarterly); daily scheduler sends, then advances `send_on` (month-end clamped) and increments `runs`; Cancel stops the series. UI: Repeat select in composer, "Repeats" column in Scheduled Appeals.
- Each segment appeal gets an `id`; email "Make a Gift" links to `/api/t/appeal/{id}` (counts click, per-IP throttled, 302 → `/donate?appeal={id}`). Donate page keeps it in sessionStorage and sends `appeal_id` with checkout; stored on transaction + Stripe metadata.
- Appeal History shows Clicks, Gifts, Raised (paid transactions attributed by appeal_id). Test copies are untracked.

## 2026 — EIN hidden, Email Links, Real Form Feedback, Events Manager (iteration_4: all pass)
- EIN removed from every public page and the frontend bundle; it is only in admin settings + donor receipt/statement emails.
- Email links: `PUBLIC_APP_URL` is now dynamic: admin-set `site_url` > `detected_site_url` (saved from Host when an admin hits /auth/me) > env fallback. Hardcoded preview links in progress/reactivation emails fixed. Admin → Campaign "Website & Notifications" section (site_url override + staff_notify_email).
- Forms: Contact/Volunteer/Member await the API, show real success/error (429 friendly), validated (name, email, contact message); "(demo)" labels removed. Public `/api/submissions` accepts only contact/volunteer/member. Staff notification email per submission/RSVP (default caringsistersclub@gmail.com, blank = off).
- Events: `events` + `event_rsvps` collections. Public GET /api/events (upcoming, spots_left), POST /api/events/{id}/rsvp (capacity, duplicate, party size checks; own rate bucket). Admin CRUD /api/admin/events, RSVP list/remove/CSV export. Confirmation email on RSVP; daily scheduler sends day-before reminders once. Admin → Events tab (AdminEvents.jsx). Public Events page now DB-driven with empty state (old mock events removed).

## 2026 — Real contact info
- org (mock.js): 600 Greenspring Terrace, Bear, DE 19701; (302) 414-5788; info@caringsistersclub.org; Mon–Fri 8–5 ET; socials YouTube/Facebook/Instagram/TikTok via new components/SocialLinks.jsx (footer + Contact "Follow Our Sisterhood"). Phone/email/address clickable. Sample-placeholder notes removed.

## 2026 — Transparency editor, Event Waitlist, Add to Calendar, Donor Self-Service (iteration_5: 100%)
- Transparency: settings doc key 'transparency' (breakdown must total 100%, stats, yearly financials, reports 990/annual/audit/other). Public GET /api/transparency, admin PUT /api/admin/transparency; Admin → Transparency tab; public page + Home stats read it (lib/useTransparency.js). "(Illustrative figures.)" shown until first publish. Media category 'report' accepts PDFs.
- Waitlist: event.waitlist_mode auto|invite. POST /api/events/{id}/waitlist; _process_waitlist runs on RSVP removal/cancel, event update, hourly + daily. Invite = 24h held seat (counts against spots_left), claim at /rsvp?token=. RSVP confirmation emails include cancel link (/rsvp?token=cancel_token). Admin RSVP panel shows waitlist with statuses.
- Calendar: Google Calendar link + /api/events/{id}/calendar.ics (times assumed ET, 2h duration, all-day if time unparseable) in confirm/reminder/promoted emails and on site.
- Donor self-service: /manage-gift page → POST /api/donor/manage-link (generic reply, 1h one-time token) → POST /api/donor/portal → Stripe Billing Portal (card update, cancel at period end, invoices; config auto-created per test/live key). Monthly receipts include reusable 60-day "Manage your gift" link. Footer + Donate (monthly) links.
- QA helper: backend/tests/qa_session.py up|down (temp admin cookie qa_tok_123).

## 2026 — Programs editor, audit fixes, locked email links, single-use manage links, cancellation alerts (iteration_6: 100%)
- Programs: `programs` collection (seeded once from old mock list; flag settings.programs_seeded), categories in settings.program_categories. Public GET /api/programs, /api/programs/{slug}; admin CRUD /api/admin/programs, POST /admin/programs/reorder, PUT /admin/program-categories. Pages: Initiatives.jsx (API), ProgramDetail.jsx (/initiatives/:slug), AdminPrograms.jsx (Admin → Programs). Media category 'program'.
- Audit: donations CSV + client donors CSV sanitize formula prefixes. Admin bootstrap: only ADMIN_OWNER_EMAILS (backend .env: vincekudjoe@gmail.com, caringsistersclub@gmail.com, admin@caringsistersclub.org) or allowed_emails become admin; owners auto-promoted on login; first-user auto-admin removed.
- Email links: PUBLIC_APP_URL = settings.site_url or env fallback only (detected host is a suggestion). Admin SiteUrlBanner with one-click "Use <origin>".
- Manage-gift tokens all single-use (atomically claimed); receipt tokens 30 days.
- Cancellations: webhook customer.subscription.updated/deleted + daily _check_cancellations → `cancellations` (unique sub_id) → staff email with /cancel-thanks?token= page (editable note, one send; reverts on provider failure).
- App error statuses use 424 instead of 502 (Cloudflare replaces 502 bodies).
- Don't write scratch files under /app/backend (uvicorn reload).

## 2026 — Program galleries/testimonials, Win-Backs, Home content editor (iteration_7: 100%)
- Programs gain gallery[{url,caption}] (≤24), testimonials (≤6, custom) and home_testimonial_ids (picked from Home list; merged on GET /api/programs/{slug}). ProgramDetail has gallery grid + lightbox + "Voices from the program".
- Home content: settings key 'home' (mission heading/title/body/quote/image, pillars ≤6 with icon allowlist, testimonials ≤12 with photo). GET /api/home-content, PUT /api/admin/home-content; Admin → Home Page tab (AdminHome.jsx, reusable ImageUpload/TestimonialsEditor); Home.jsx reads via lib/useHomeContent.js.
- Win-backs: GET /api/admin/winbacks — returned = paid txn created after thanked_at not from the cancelled sub; WinBacks card on Admin → Donors.
- Save Live Address is a user action on production (Admin banner button).

## 2026 — About editor, member stories, program sign-ups, monthly impact email (iteration_8)
- About: settings key 'about' (hero_subtitle, mission title/body/image, values ≤8, story milestones ≤12 with photo). GET /api/about-content, PUT /api/admin/about-content; Admin → About Page (AdminAbout.jsx); About.jsx reads via useAboutContent.
- Stories: public POST /api/stories (+ POST /api/stories/photo public upload, category 'story', hidden from /api/media list), admin GET /api/admin/stories, POST /{id}/approve {target:'home'|program_id, quote} → appended testimonial (added_at), /{id}/reject. ShareStory dialog on Home + program pages. Admin → Stories & Updates.
- Program sign-ups: POST /api/programs/{slug}/signup → submissions type program_signup + staff notify + confirmation email. ProgramSignup form on program pages.
- Monthly impact email: gallery items/testimonials carry added_at; _impact_content(last 31 days); recipients = paid monthly donors not cancelled; auto days 1–3 once/month (impact_emails log); admin preview/test/send at /api/admin/impact-email/*.

## 2026 — Story requests, Program interest report, Impact email tracking, Volunteer hours (iteration_9: 100%)
- Story requests: daily _send_story_requests (setting story_requests_enabled, toggle in Stories & Updates) emails program_signup submissions once after 60 days → /initiatives/<slug>?share=1 (ShareStory autoOpen). Signups store data.program_slug.
- Reports: GET /api/admin/reports/program-signups?months=N; Admin → Reports tab (AdminReports.jsx: table, trends, CSV + volunteer hours review); SignupCard on Programs tab.
- Impact tracking: each send has impact_emails.id (cid) + impact_recipients {cid,rid,opened_at,clicked_at,opens,clicks}; pixel /api/t/impact/{cid}/open.gif, clicks /api/t/impact/{cid}/click?r=&u=/path (relative only). GET /api/admin/impact-email/history. Test sends untracked.
- Volunteer hours: public POST /api/volunteer-hours (pending), admin approve/reject, public GET /api/volunteer-hours/summary → Transparency "volunteer impact" section; LogHours form on /volunteer.
- Admin tab persists in sessionStorage.

## 2026 — Volunteer thank-yous, leaderboard, story-request results, sign-up stages (iteration_10: 100%)
- _send_volunteer_thanks: one email per volunteer per UTC day (volunteer_thanks unique email+day) combining approved-unthanked entries; runs after approve + hourly.
- Leaderboard: HoursIn.leaderboard opt-in (latest entry decides); GET /api/volunteer-hours/leaderboard (top 10 this year, "First L."). Shown on /volunteer.
- GET /api/admin/reports/story-requests (invites, submitted after invite, rate, approved). PUT /api/admin/submissions/{id}/stage (new/contacted/enrolled/not_fit); program-signups report adds contacted_pct/enrolled_pct. StageSelect in Form Submissions.
- "Log more hours" now resets the leaderboard opt-in checkbox (fixed iteration 11).

## 2026 — Volunteer milestones, enrollment reminders, program capacity, Year in Review (iteration_11)
- Milestones: VOL_MILESTONES=(10,50,100) (do NOT rename to MILESTONES — that name is the fundraising goal list). _award_milestones records db.volunteer_milestones {email,scope:'all'|'year:YYYY',threshold} once (upsert); evaluated inside _send_volunteer_thanks; badges shown in thank-you email + separate badge email per milestone.
- Enrollment reminders: _overdue_q (program_signup, stage new/missing, >=7 days); daily digest to staff_notify_email via _send_enrollment_reminders (scheduled_runs key enroll-remind:DATE); POST /api/admin/signups/send-reminders; counts.program_signup.overdue; Admin Form Submissions overdue bar/filter/badges.
- Capacity: ProgramIn.capacity (0=unlimited); _seats_taken counts signups not not_fit, excluding waitlisted unless enrolled; seats_left/full on public/admin program endpoints; full → signup stored waitlist:true + data.list='Waitlist' + waitlist confirmation email. SeatsBadge on Initiatives cards/program page.
- Year in Review: GET /api/year-in-review/{year} (public only if year in settings.site.yir_public), admin GET/PUT /api/admin/year-in-review/{year}; page /year-in-review/:year with stats, featured approved stories, share bar; admin card in Reports.

## Backlog
- P1: Open Graph share image/meta for Year in Review; "Promote from waitlist" email to waitlisted sign-ups when a seat frees.
- P2: Milestone badges shown publicly on leaderboard; scheduler failure dashboard.
