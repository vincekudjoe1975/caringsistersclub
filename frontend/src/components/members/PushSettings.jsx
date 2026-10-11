import React, { useEffect, useState } from 'react';
import { BellRing, Loader2, Moon } from 'lucide-react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const PREFS = [['push_news', 'New announcements'], ['push_prayer', 'New prayer requests and praise reports'], ['push_events', 'Gatherings and sessions I signed up for (the day before)'], ['push_votes', 'Votes opening and closing soon'], ['push_bday', "Sisters' birthdays (and my own)"], ['push_weekly', 'Sunday evening "This Week" summary']];

const timeCls = 'w-full mt-1.5 rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px] bg-white font-normal focus:outline-none focus:border-[#B4247E]';

const supported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
const toKey = (b64) => {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
};

export const syncPush = async () => {
  if (!supported() || Notification.permission !== 'granted') return null;
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  const { data } = await api.get('/members/push/config', { params: { endpoint: sub?.endpoint || '' } });
  if (sub && !data.registered) {
    await api.post('/members/push/subscribe', sub.toJSON());
    return (await api.get('/members/push/config', { params: { endpoint: sub.endpoint } })).data;
  }
  return data;
};

export const PushSettings = ({ p, set }) => {
  const { toast } = useToast();
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [cfg, setCfg] = useState(null);
  const refresh = () => syncPush().then((d) => { if (d) { setCfg(d); setOn(d.registered); } else api.get('/members/push/config').then(({ data }) => setCfg(data)).catch(() => {}); }).catch(() => {});
  useEffect(() => { if (supported()) refresh(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const toggle = async () => {
    setBusy(true);
    try {
      const key = cfg?.public_key;
      const perm = await Notification.requestPermission();
      if (perm !== 'granted') throw new Error('Notifications are blocked. Allow them for this site in your phone settings, then try again.');
      const reg = await navigator.serviceWorker.ready;
      const cur = await reg.pushManager.getSubscription();
      if (on && cur) {
        await api.post('/members/push/unsubscribe', { endpoint: cur.endpoint }); await cur.unsubscribe(); setOn(false);
        toast({ title: 'Phone alerts turned off' });
      } else {
        const pk = key || (await api.get('/members/push/config')).data.public_key;
        const sub = cur || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toKey(pk) });
        const { data } = await api.post('/members/push/subscribe', sub.toJSON());
        toast({ title: 'Phone alerts are on', description: `Registered: ${data.kind}` });
      }
      refresh();
    } catch (ex) { toast({ title: 'Could not change alerts', description: ex?.response?.data?.detail || ex.message, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const testMe = async () => {
    try { const { data } = await api.post('/members/push/test-self'); toast({ title: `Test sent to ${data.sent} of your device${data.devices === 1 ? '' : 's'}`, description: 'It should arrive within a few seconds.' }); }
    catch (ex) { toast({ title: 'Could not send test', description: ex?.response?.data?.detail, variant: 'destructive' }); }
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
          <p data-testid="push-status" className="text-[12.5px] text-[#241019]/55 mt-2">{on ? 'On for this device (confirmed with the Club).' : 'Off for this device.'}</p>
          {cfg?.device_list?.length > 0 && (
            <div data-testid="push-devices" className="mt-3 text-[13px]">
              <p className="font-semibold text-[#3B0A2E]">Devices getting your alerts</p>
              <ul className="mt-1 space-y-0.5">{cfg.device_list.map((d, i) => <li key={i} className="text-[#241019]/70">{d.kind}{d.this ? ' (this device)' : ''}</li>)}</ul>
              <button type="button" data-testid="push-test-self-btn" onClick={testMe} className="mt-2 min-h-[40px] text-[13.5px] font-semibold text-[#B4247E] underline">Send a test alert to my devices</button>
            </div>
          )}
        </>
      )}
      <p className="text-[13px] font-semibold text-[#3B0A2E] mt-4">Alert me about</p>
      {PREFS.map(([k, l]) => (
        <label key={k} className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-3 cursor-pointer">
          <input data-testid={`profile-${k.replace('_', '-')}`} type="checkbox" checked={p[k] !== false} onChange={(e) => set(k, e.target.checked)} className="mt-0.5 accent-[#B4247E] w-5 h-5 shrink-0" />
          <span>{l}</span>
        </label>
      ))}
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-5 pt-4 border-t border-[#3B0A2E]/8 cursor-pointer">
        <input data-testid="profile-quiet-on" type="checkbox" checked={!!p.quiet_on} onChange={(e) => set('quiet_on', e.target.checked)} className="mt-0.5 accent-[#B4247E] w-5 h-5 shrink-0" />
        <span className="flex items-center gap-1.5"><Moon size={14} className="text-[#B4247E]" /> Quiet hours: hold alerts until they end</span>
      </label>
      {p.quiet_on && (
        <div className="grid grid-cols-2 gap-3 mt-3" data-testid="quiet-hours-fields">
          <label className="text-[13px] font-semibold text-[#3B0A2E]">From<input data-testid="profile-quiet-start" type="time" value={p.quiet_start || '21:00'} onChange={(e) => set('quiet_start', e.target.value)} className={timeCls} /></label>
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Until<input data-testid="profile-quiet-end" type="time" value={p.quiet_end || '08:00'} onChange={(e) => set('quiet_end', e.target.value)} className={timeCls} /></label>
          <p className="col-span-2 text-[12.5px] text-[#241019]/55">Eastern time. Alerts that arrive during quiet hours are delivered when they end.</p>
        </div>
      )}
    </div>
  );
};
