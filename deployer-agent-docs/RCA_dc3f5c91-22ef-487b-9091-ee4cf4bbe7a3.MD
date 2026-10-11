# RCA — Web push reaches desktop but not phones (Android PWA / iPhone PWA)

**Deployment:** caring-sisters-clone  ·  **Run:** dc3f5c91-22ef-487b-9091-ee4cf4bbe7a3 (active, success)
**DB inspected:** caring-sisters-clone-test_database (production/Atlas, read-only)

## Summary / Root cause
This is **not** a server, VAPID, or deployment failure. The backend is healthy and delivers every push it has a subscription for. The phones don't receive anything because **the production database has no push subscription for the phones**:

- `push_subs` holds **only 2 documents total**, and **neither is an Apple endpoint**:
  1. `wns2-bn3p.notify.windows.com` (Windows WNS) → `user_99dc2fb38790`
  2. `fcm.googleapis.com/fcm/send/…` (single FCM endpoint) → `user_d96cb210ebf7`
- **No `web.push.apple.com` subscription exists** ⇒ the iPhone home-screen PWA never persisted a subscription server-side, so iOS can receive nothing.
- Only **one** FCM endpoint exists, but the user describes **two** Chrome devices (desktop Chrome + Android Chrome) — both of which use `fcm.googleapis.com`. Only one persisted. The one FCM sub is almost certainly the **working desktop**; the **Android phone's subscription is not in the DB**.
- The two existing subs sit under **two different user_ids**, indicating an account/identity split across devices.

So despite the phone UI showing **"On for this device,"** there is no matching row in `push_subs` for that device. The server simply has nothing to send to the phones.

## Evidence
- `push_subs` find (count=2): endpoints/user_ids/updated_at as above. No apple host.
- `push_log` latest sends: `members:5` but `delivered:2, failed:0, expired:0, held:0` — server delivers to exactly the 2 subs it has, with zero failures/expiries. (If the phone subs existed and were dead you'd see `expired`/`failed` > 0 and `410` in logs; you don't.)
- Backend logs (24h): **no** `Push failed`, `Push loop error`, `403 BadJwtToken`, `410`, or `400`. `POST /api/members/push/subscribe` → 200.
- Secrets present & non-empty: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`. No 403 BadJwtToken + successful FCM delivery ⇒ VAPID (incl. SUBJECT = `mailto:` form) is valid. (Secret values are sealed and were not read directly.)
- `users.member_profile`: both users `quiet_on:false`, push_* prefs `true` ⇒ quiet hours / prefs are NOT the cause.

## Why "On for this device" shows true but no sub is stored (most probable, not yet reproduced in code)
1. **Account/identity mismatch** — the phone is logged into (or subscribed under) a different member account than the desktop; its subscription either landed on a non-targeted user_id or was not associated with the member being sent to. The two distinct user_ids in `push_subs` support this.
2. **Client toggle not reconciled with server** — the "On for this device" indicator is driven by a local flag / `PushManager.getSubscription()` existing in the browser, while the POST to `/api/members/push/subscribe` either never ran for that logged-in member or didn't persist. The UI should reflect an actual `push_subs` row, not just a local flag.
3. **iOS specifics** — iOS Web Push requires iOS **16.4+** and the app launched from the **Home-Screen-installed PWA**; permission must be granted inside that installed context. If any of these is unmet, Safari never creates a `web.push.apple.com` subscription — matching the total absence of an Apple endpoint.

## Recommended actions
### Code (E1 — source side)
- In the `/api/members/push/subscribe` handler, confirm the incoming `PushSubscription` is persisted to `push_subs` **keyed to the authenticated member's user_id**, and add a log line on save (endpoint host + user_id) so new-device subscribes are traceable.
- Make the "On for this device" indicator reflect a real server-side `push_subs` row for the current member (reconcile client state with DB), so a device can't show "On" with no stored subscription.
- Verify the service worker on Android calls `showNotification()` for every `push` event (a silent push with no `showNotification` is dropped by Chrome).
- Confirm iOS path is supported (manifest + home-screen install + permission prompt inside the installed PWA); surface a clear message when iOS < 16.4 or not installed.

### User
- Ensure the **same member account** is logged in on desktop, Android, and iPhone. The DB currently shows subscriptions under two different accounts.
- **Android:** re-open the installed PWA, toggle notifications off then on to force a fresh `/push/subscribe`, and confirm a new `fcm.googleapis.com` row appears under the correct account; check that battery optimization isn't suppressing FCM.
- **iPhone:** use iOS 16.4+, **Add to Home Screen**, open from that icon, and allow notifications there — then a `web.push.apple.com` row should appear.

## Not the cause (ruled out)
- VAPID keys/subject (deliveries succeed, no 403). Quiet hours / push prefs (all permissive). Server push loop (no errors, no failures logged). Deployment/build/tier (active run healthy).
