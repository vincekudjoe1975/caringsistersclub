import React, { useCallback, useEffect, useState } from 'react';
import { Award, Clock, Loader2, Trash2 } from 'lucide-react';
import { api } from '../../lib/api';

const inputCls = 'w-full mt-1.5 rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';
const today = () => new Date().toLocaleDateString('en-CA');
const STATUS = { pending: 'bg-amber-100 text-amber-800', approved: 'bg-emerald-100 text-emerald-800', rejected: 'bg-red-100 text-red-700' };

export const MyHours = () => {
  const [d, setD] = useState(null);
  const [f, setF] = useState({ date: today(), hours: '', activity: '', note: '' });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const load = useCallback(() => api.get('/members/hours').then(({ data }) => setD(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setMsg('');
    try { await api.post('/members/hours', { ...f, hours: Number(f.hours) }); setF({ date: today(), hours: '', activity: '', note: '' }); setMsg('Thank you! Your hours were sent to staff for approval.'); load(); }
    catch (ex) { setMsg(ex?.response?.data?.detail || 'Could not save.'); }
    finally { setBusy(false); }
  };
  const remove = async (id) => { await api.delete(`/members/hours/${id}`).catch(() => {}); load(); };
  if (!d) return <div className="py-16 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  return (
    <div data-testid="my-hours" className="space-y-6">
      <div>
        <h2 className="font-serif text-[26px] text-[#3B0A2E] font-semibold">My volunteer hours</h2>
        <p data-testid="my-hours-total" className="text-[15px] text-[#241019]/75 mt-1"><span className="font-semibold text-[#B4247E] text-[22px]">{d.total}</span> approved hours{d.pending ? ` · ${d.pending} waiting for approval` : ''}{d.next ? ` · ${Math.round((d.next - d.total) * 100) / 100} to your ${d.next}-hour badge` : ''}</p>
      </div>
      <div className="grid grid-cols-5 gap-2 sm:gap-4 max-w-xl" data-testid="my-hours-badges">
        {d.badges.map((b) => (
          <div key={b.hours} data-testid={`hours-badge-${b.hours}`} className={`aspect-square rounded-full flex flex-col items-center justify-center border-[3px] transition-transform ${b.earned ? 'bg-[#3B0A2E] border-[#CBA24B] text-[#CBA24B] hover:scale-105' : 'bg-white border-dashed border-[#3B0A2E]/20 text-[#3B0A2E]/30'}`}>
            <Award size={18} /><span className="font-serif font-semibold text-[15px] sm:text-[18px] leading-none mt-0.5">{b.hours}h</span>
          </div>
        ))}
      </div>
      <form onSubmit={submit} data-testid="hours-form" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 max-w-xl">
        <p className="font-semibold text-[#3B0A2E] flex items-center gap-2 mb-1"><Clock size={16} className="text-[#B4247E]" /> Log hours</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Date<input data-testid="hours-date" type="date" max={today()} required value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} className={inputCls} /></label>
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Hours<input data-testid="hours-hours" type="number" step="0.25" min="0.25" max="24" required value={f.hours} onChange={(e) => setF({ ...f, hours: e.target.value })} className={inputCls} /></label>
        </div>
        <label className="block text-[13px] font-semibold text-[#3B0A2E] mt-3">Activity<input data-testid="hours-activity" required maxLength={120} placeholder="e.g. Food pantry sorting" value={f.activity} onChange={(e) => setF({ ...f, activity: e.target.value })} className={inputCls} /></label>
        <label className="block text-[13px] font-semibold text-[#3B0A2E] mt-3">Notes (optional)<textarea data-testid="hours-note" rows={2} maxLength={500} value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} className={inputCls} /></label>
        <button data-testid="hours-submit" disabled={busy} className="btn-magenta rounded-full px-6 py-2.5 font-semibold mt-4 w-full sm:w-auto flex items-center justify-center gap-2 disabled:opacity-60">{busy && <Loader2 size={14} className="animate-spin" />} Submit hours</button>
        {msg && <p data-testid="hours-msg" className="text-[13px] text-[#3B0A2E] mt-2">{msg}</p>}
      </form>
      {d.entries.length > 0 && (
        <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 max-w-xl" data-testid="hours-entries">
          {d.entries.map((e) => (
            <div key={e.id} data-testid={`hours-entry-${e.id}`} className="py-2.5 border-t first:border-t-0 border-[#3B0A2E]/8 flex items-center gap-3 text-[13.5px]">
              <div className="min-w-0 flex-1"><p className="font-semibold text-[#3B0A2E] break-words">{e.activity || e.program}</p><p className="text-[#241019]/55">{e.date} · {e.hours}h</p></div>
              <span className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${STATUS[e.status] || ''}`}>{e.status}</span>
              {e.status === 'pending' && <button data-testid={`hours-delete-${e.id}`} onClick={() => remove(e.id)} aria-label="Remove" className="w-9 h-9 flex items-center justify-center text-[#241019]/50 hover:text-red-600"><Trash2 size={14} /></button>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
