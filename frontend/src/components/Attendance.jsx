import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, X, Check, UserX, CheckCheck } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

export const AttendancePanel = ({ program, onClose }) => {
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get(`/admin/programs/${program.id}/attendance`).then(({ data }) => setD(data)).catch(() => setD({ items: [] })), [program.id]);
  useEffect(() => { load(); }, [load]);
  const save = async (body) => {
    setBusy(true);
    try { await api.post(`/admin/programs/${program.id}/attendance`, body); await load(); }
    catch (err) { toast({ title: 'Save failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const set = (it, v) => save({ updates: { [it.id]: it.attendance === v ? null : v } });
  const counts = d ? { a: d.items.filter((i) => i.attendance === 'attended').length, n: d.items.filter((i) => i.attendance === 'no_show').length } : null;
  const toggle = (it, v, Icon, label, on) => (
    <button disabled={busy} onClick={() => set(it, v)} data-testid={`attendance-${v}-btn`} className={`px-3 py-1.5 rounded-full text-[12px] font-semibold flex items-center gap-1 border transition-colors ${it.attendance === v ? on : 'text-[#3B0A2E]/60 border-[#3B0A2E]/15'}`}><Icon size={13} /> {label}</button>
  );
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} data-testid="attendance-panel" className="bg-white rounded-2xl max-w-2xl w-full max-h-[88vh] overflow-y-auto p-7">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Attendance · {program.title}</h3>
            {counts && <p className="text-[12.5px] text-[#241019]/60" data-testid="attendance-summary">{counts.a} attended · {counts.n} no-show · {d.items.length - counts.a - counts.n} unmarked</p>}
          </div>
          <button onClick={onClose} data-testid="attendance-close-btn" className="p-2 text-[#3B0A2E]"><X size={18} /></button>
        </div>
        {!d ? <Loader2 className="animate-spin text-[#B4247E] mx-auto" /> : d.items.length === 0 ? <p className="text-[13.5px] text-[#241019]/55 text-center py-8" data-testid="attendance-empty">No seated sisters for this session.</p> : (
          <>
            <button disabled={busy} onClick={() => save({ all: 'attended' })} data-testid="attendance-mark-all-btn" className="mb-4 text-[12.5px] font-semibold px-4 py-2 rounded-full text-white bg-[#3B0A2E] flex items-center gap-1.5 disabled:opacity-50"><CheckCheck size={14} /> Mark all attended</button>
            <div className="divide-y divide-[#3B0A2E]/8">
              {d.items.map((it) => (
                <div key={it.id} className="flex items-center justify-between gap-3 py-2.5" data-testid="attendance-row">
                  <div><p className="font-semibold text-[#3B0A2E] text-[14px]">{it.name}</p><p className="text-[11.5px] text-[#241019]/55">{it.email}</p></div>
                  <div className="flex gap-2">
                    {toggle(it, 'attended', Check, 'Attended', 'bg-[#e9f3e6] text-[#3c7a2f] border-[#3c7a2f]/30')}
                    {toggle(it, 'no_show', UserX, 'No-show', 'bg-[#f5e9ec] text-[#9b3b4f] border-[#9b3b4f]/30')}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[11.5px] text-[#241019]/50 mt-4">Once attendance is taken, feedback emails go only to sisters marked Attended.</p>
          </>
        )}
      </div>
    </div>
  );
};

export const AttendanceReport = () => {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get('/admin/reports/attendance').then(({ data }) => setItems(data.items)).catch(() => setItems([])); }, []);
  if (!items || items.length === 0) return null;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="attendance-report">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-4"><CheckCheck size={18} className="text-[#B4247E]" /> Session attendance</h3>
      <table className="w-full text-left text-[13px]">
        <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50">{['Session', 'Dates', 'Seated', 'Attended', 'No-show', 'Unmarked', 'Attendance'].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
        <tbody>{items.map((r) => (
          <tr key={r.id} className="border-t border-[#3B0A2E]/8" data-testid="attendance-report-row">
            <td className="px-3 py-2.5 font-semibold text-[#3B0A2E]">{r.title}</td>
            <td className="px-3 py-2.5 text-[#241019]/60">{r.start_date}{r.end_date !== r.start_date ? ` – ${r.end_date}` : ''}</td>
            <td className="px-3 py-2.5">{r.seated}</td><td className="px-3 py-2.5">{r.attended}</td><td className="px-3 py-2.5">{r.no_show}</td><td className="px-3 py-2.5">{r.unmarked}</td>
            <td className="px-3 py-2.5 font-bold text-[#B4247E]" data-testid="attendance-report-pct">{r.attendance_pct === null ? '—' : `${r.attendance_pct}%`}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
};
