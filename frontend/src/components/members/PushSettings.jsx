import React, { useEffect, useState } from 'react';
import { BellRing, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const supported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
const toKey = (b64) => {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
};

export const PushSettings = ({ p, set }) => {
  const { toast } = useToast();
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!supported()) return;
    navigator.serviceWorker.ready.then((r) => r.pushManager.getSubscription()).then((s) => setOn(!!s && Notification.permission === 'granted'));
  }, []);
  const toggle = async () => {
    setBusy(true);
    try {
      const reg = await navigator.serviceWorker.ready;
      const cur = await reg.pushManager.getSubscription();
      if (on && cur) {
        await api.post('/members/push/unsubscribe', { endpoint: cur.endpoint }); await cur.unsubscribe(); setOn(false);
        toast({ title: 'Phone alerts turned off' });
      } else {
        if ((await Notification.requestPermission()) !== 'granted') throw new Error('Notifications are blocked in your browser settings.');
        const { data } = await api.get('/members/push/config');
        const sub = cur || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toKey(data.public_key) });
        await api.post('/members/push/subscribe', sub.toJSON()); setOn(true);
        toast({ title: 'Phone alerts are on' });
      }
    } catch (ex) { toast({ title: 'Could not change alerts', description: ex?.response?.data?.detail || ex.message, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="push-settings" className="mt-7 bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
      <p className="font-semibold text-[#3B0A2E] flex items-center gap-2"><BellRing size={16} className="text-[#B4247E]" /> Phone alerts</p>
      {!supported() ? (
        <p data-testid="push-unsupported" className="text-[13.5px] text-[#241019]/65 mt-1">This browser can't receive alerts. On iPhone, add the site to your home screen first, then open it from there.</p>
      ) : (
        <>
          <p className="text-[13.5px] text-[#241019]/65 mt-1">Get a notification on this phone when there's news from the Club.</p>
          <button type="button" data-testid="push-toggle-btn" disabled={busy} onClick={toggle}
            className={`mt-3 min-h-[44px] rounded-full px-5 py-2.5 text-[14px] font-semibold flex items-center gap-2 disabled:opacity-60 ${on ? 'border border-[#3B0A2E]/20 text-[#3B0A2E]' : 'btn-magenta'}`}>
            {busy && <Loader2 size={14} className="animate-spin" />} {on ? 'Turn off on this phone' : 'Turn on phone alerts'}
          </button>
          <p data-testid="push-status" className="text-[12.5px] text-[#241019]/55 mt-2">{on ? 'On for this device.' : 'Off for this device.'}</p>
        </>
      )}
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-4 cursor-pointer">
        <input data-testid="profile-push-news" type="checkbox" checked={p.push_news !== false} onChange={(e) => set('push_news', e.target.checked)} className="mt-0.5 accent-[#B4247E] w-5 h-5 shrink-0" />
        <span>New announcements</span>
      </label>
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-3 cursor-pointer">
        <input data-testid="profile-push-prayer" type="checkbox" checked={p.push_prayer !== false} onChange={(e) => set('push_prayer', e.target.checked)} className="mt-0.5 accent-[#B4247E] w-5 h-5 shrink-0" />
        <span>New prayer requests and praise reports</span>
      </label>
    </div>
  );
};
