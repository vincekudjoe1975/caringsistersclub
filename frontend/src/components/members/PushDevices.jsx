import React, { useCallback, useEffect, useState } from 'react';
import { Smartphone, Monitor, Loader2, Send, Search } from 'lucide-react';
import { api } from '../../lib/api';

const ago = (iso) => {
  if (!iso) return '';
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  return m < 60 ? `${Math.max(1, m)}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`;
};
const isPhone = (k) => k.startsWith('iPhone') || k.startsWith('Android');

const Device = ({ d, i, uid }) => (
  <li data-testid={`push-device-${uid}-${i}`} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px] text-[#241019]/75">
    {isPhone(d.kind) ? <Smartphone size={13} className="text-[#B4247E]" /> : <Monitor size={13} className="text-[#3B0A2E]/60" />}
    <span className="font-semibold text-[#3B0A2E]">{d.kind}</span>
    <span>· registered {ago(d.updated_at)}</span>
    {d.last_ok_at && <span className="text-[#245C32]">· last delivered {ago(d.last_ok_at)}</span>}
    {d.last_fail_at && (!d.last_ok_at || d.last_fail_at > d.last_ok_at) && <span className="text-[#9B1C3A]">· last delivery failed {ago(d.last_fail_at)}</span>}
  </li>
);

export const PushDevices = ({ toast }) => {
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState('');
  const load = useCallback(() => api.get('/admin/members/push/devices').then(({ data }) => setRows(data.rows)).catch(() => setRows([])), []);
  useEffect(() => { load(); }, [load]);
  const test = async (r) => {
    setBusy(r.user_id);
    try { const { data } = await api.post(`/admin/members/push/test-member/${r.user_id}`); toast({ title: `Test sent to ${data.sent} of ${data.devices} device${data.devices === 1 ? '' : 's'} for ${r.name || r.email}` }); load(); }
    catch (ex) { toast({ title: 'Could not send test', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  if (!rows) return <div className="py-6 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" size={20} /></div>;
  const shown = rows.filter((r) => `${r.name} ${r.email}`.toLowerCase().includes(q.toLowerCase()));
  const phones = rows.filter((r) => r.devices.some((d) => isPhone(d.kind))).length;
  return (
    <div data-testid="push-devices-admin" className="mt-8">
      <p className="font-serif text-[18px] text-[#3B0A2E] font-semibold">Registered devices</p>
      <p data-testid="push-devices-summary" className="text-[13px] text-[#241019]/60 mb-3">{phones} member{phones === 1 ? '' : 's'} with a phone registered. If a sister isn't getting alerts and shows no phone here, ask her to open the app on her phone and turn phone alerts off and back on in My Profile.</p>
      <label className="relative block mb-3 max-w-sm">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#241019]/40" />
        <input data-testid="push-devices-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search members" className="w-full rounded-xl border border-[#3B0A2E]/15 pl-8 pr-3 py-2 text-[13.5px] bg-white focus:outline-none focus:border-[#B4247E]" />
      </label>
      <ul className="divide-y divide-[#3B0A2E]/10 rounded-2xl bg-white border border-[#3B0A2E]/10 max-h-[420px] overflow-y-auto">
        {shown.map((r) => (
          <li key={r.user_id} data-testid={`push-devices-row-${r.user_id}`} className="px-4 py-3 flex flex-wrap items-start gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-semibold text-[#3B0A2E] truncate">{r.name || r.email} <span className="font-normal text-[12px] text-[#241019]/50">{r.email}</span></p>
              {r.devices.length ? <ul className="mt-1 space-y-0.5">{r.devices.map((d, i) => <Device key={i} d={d} i={i} uid={r.user_id} />)}</ul>
                : <p data-testid={`push-devices-none-${r.user_id}`} className="text-[12.5px] text-[#241019]/50 mt-0.5">No devices registered</p>}
            </div>
            {r.devices.length > 0 && (
              <button type="button" data-testid={`push-devices-test-${r.user_id}`} disabled={busy === r.user_id} onClick={() => test(r)} className="rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5 hover:bg-[#F7EFE9] transition-colors disabled:opacity-60">
                {busy === r.user_id ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Send test
              </button>
            )}
          </li>
        ))}
        {!shown.length && <li className="px-4 py-4 text-[13px] text-[#241019]/55">No members match.</li>}
      </ul>
    </div>
  );
};
