import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { Check, X, Clock3, Pencil, Trash2, Undo2, RotateCcw, Loader2 } from 'lucide-react';

const inp = 'rounded-lg border border-[#3B0A2E]/15 px-2.5 py-1.5 text-[13px] focus:outline-none focus:border-[#B4247E] w-full';
const icon = 'p-1.5 rounded-full hover:bg-[#faf2f7] transition-colors';

function EditRow({ h, programs, onCancel, onSaved }) {
  const { toast } = useToast();
  const [f, setF] = useState({ hours: h.hours, date: h.date, program_id: h.program_id || '', activity: h.activity || '', note: h.note || '' });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));
  const save = async () => {
    setBusy(true);
    try { await api.put(`/admin/volunteer-hours/${h.id}`, { ...f, hours: Number(f.hours) }); toast({ title: 'Entry updated', description: 'Totals and badges were recalculated.' }); onSaved(); }
    catch (e) { toast({ title: 'Could not save', description: e?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <tr className="border-t border-[#3B0A2E]/8 bg-[#fdf8fb]" data-testid={`hours-edit-row-${h.id}`}>
      <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E]">{h.name}</p><p className="text-[11.5px] text-[#241019]/55">{h.email}</p></td>
      <td className="px-3 py-2.5">{'activity' in h && !h.program_id
        ? <input value={f.activity} onChange={set('activity')} className={inp} data-testid="hours-edit-activity" />
        : <select value={f.program_id} onChange={set('program_id')} className={inp} data-testid="hours-edit-program">{!programs.some((p) => p.id === f.program_id) && <option value={f.program_id}>{h.program}</option>}{programs.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}</select>}</td>
      <td className="px-3 py-2.5"><input type="date" value={f.date} onChange={set('date')} className={inp} data-testid="hours-edit-date" /></td>
      <td className="px-3 py-2.5 w-[90px]"><input type="number" min="0.25" max="24" step="0.25" value={f.hours} onChange={set('hours')} className={inp} data-testid="hours-edit-hours" /></td>
      <td className="px-3 py-2.5"><input value={f.note} onChange={set('note')} className={inp} placeholder="Note" data-testid="hours-edit-note" /></td>
      <td className="px-3 py-2.5 text-right whitespace-nowrap">
        <button onClick={save} disabled={busy} data-testid="hours-edit-save-btn" className="btn-magenta rounded-full px-3 py-1 text-[12px] font-semibold inline-flex items-center gap-1 disabled:opacity-60">{busy ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />} Save</button>
        <button onClick={onCancel} data-testid="hours-edit-cancel-btn" className="ml-1 text-[12px] font-semibold text-[#241019]/60 px-2">Cancel</button>
      </td>
    </tr>
  );
}

export function HoursReview({ BadgeWallSetting }) {
  const [d, setD] = useState(null);
  const [tab, setTab] = useState('pending');
  const [editing, setEditing] = useState('');
  const [programs, setPrograms] = useState([]);
  const { toast } = useToast();
  const load = useCallback(() => api.get('/admin/volunteer-hours').then(({ data }) => setD({ items: data.items || [], removed: data.removed || [] })).catch(() => setD({ items: [], removed: [] })), []);
  useEffect(() => { load(); api.get('/programs').then(({ data }) => setPrograms(Array.isArray(data) ? data : data.items || [])).catch(() => {}); }, [load]);
  const act = async (h, action, body) => {
    const msg = { approve: 'Hours approved', reject: 'Entry declined', pending: 'Moved back to Pending', remove: 'Entry removed (kept in the Removed log)', restore: 'Entry restored' };
    try { await api.post(`/admin/volunteer-hours/${h.id}/${action}`, body || {}); toast({ title: msg[action] }); load(); }
    catch (err) { toast({ title: 'Action failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  const remove = (h) => {
    const reason = window.prompt(`Remove ${h.hours}h for ${h.name}? It stops counting in totals, badges and the leaderboard, and moves to the Removed log.\n\nReason (optional):`, '');
    if (reason !== null) act(h, 'remove', { reason });
  };
  const purge = async (h) => {
    if (!window.confirm(`Delete this entry for good? ${h.name}, ${h.hours}h on ${h.date}. This can't be undone.`)) return;
    try { await api.delete(`/admin/volunteer-hours/${h.id}`); toast({ title: 'Entry deleted for good' }); load(); }
    catch (err) { toast({ title: 'Delete failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  if (!d) return null;
  const { items, removed } = d;
  const approved = items.filter((h) => h.status === 'approved').reduce((s, h) => s + h.hours, 0);
  const shown = tab === 'removed' ? removed : items.filter((h) => (tab === 'pending' ? h.status === 'pending' : h.status !== 'pending'));
  const tabs = [['pending', `Pending (${items.filter((h) => h.status === 'pending').length})`], ['reviewed', 'Reviewed'], ['removed', `Removed (${removed.length})`]];
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6" data-testid="hours-review">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Clock3 size={18} className="text-[#B4247E]" /> Volunteer Hours <span className="text-[13px] font-sans font-normal text-[#241019]/55" data-testid="hours-approved-total">({approved.toFixed(1)} approved hours)</span></h3>
        {BadgeWallSetting && <BadgeWallSetting />}
        <div className="inline-flex gap-1 p-1 rounded-full bg-[#faf2f7]">
          {tabs.map(([k, l]) => (
            <button key={k} onClick={() => { setTab(k); setEditing(''); }} data-testid={`hours-tab-${k}`} className={`px-4 py-1.5 rounded-full text-[12.5px] font-semibold ${tab === k ? 'text-white' : 'text-[#3B0A2E]'}`} style={tab === k ? { background: '#3B0A2E' } : {}}>{l}</button>
          ))}
        </div>
      </div>
      {shown.length === 0 ? <p className="text-[13px] text-[#241019]/55 text-center py-6" data-testid="hours-empty">{tab === 'pending' ? 'No hours waiting for review.' : tab === 'removed' ? 'Nothing has been removed.' : 'Nothing reviewed yet.'}</p> : (
        <div className="overflow-x-auto"><table className="w-full text-left text-[13px]"><tbody>{shown.map((h) => (editing === h.id
          ? <EditRow key={h.id} h={h} programs={programs} onCancel={() => setEditing('')} onSaved={() => { setEditing(''); load(); }} />
          : (
          <tr key={h.id} className="border-t border-[#3B0A2E]/8" data-testid="hours-row">
            <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E]">{h.name}</p><p className="text-[11.5px] text-[#241019]/55">{h.email}</p></td>
            <td className="px-3 py-2.5">{h.activity || h.program}</td>
            <td className="px-3 py-2.5 text-[#241019]/65">{h.date}</td>
            <td className="px-3 py-2.5 font-bold text-[#3B0A2E]">{h.hours}h</td>
            <td className="px-3 py-2.5 text-[#241019]/65 max-w-[220px]">
              <p className="truncate" title={h.note}>{h.note}</p>
              {h.edits?.length > 0 && <p className="text-[11px] text-[#241019]/45" data-testid="hours-edited-note">Edited by {h.edits[h.edits.length - 1].by}</p>}
              {h.status === 'removed' && <p className="text-[11px] text-[#9b3b4f]" data-testid="hours-removed-info">Removed by {h.removed_by} on {(h.removed_at || '').slice(0, 10)}{h.removed_reason ? `: ${h.removed_reason}` : ''}</p>}
            </td>
            <td className="px-3 py-2.5 text-right whitespace-nowrap">
              {h.status === 'pending' && <>
                <button onClick={() => act(h, 'approve')} data-testid="hours-approve-btn" title="Approve" className={`${icon} text-[#3c7a2f]`}><Check size={16} /></button>
                <button onClick={() => act(h, 'reject')} data-testid="hours-reject-btn" title="Decline" className={`${icon} text-red-500`}><X size={16} /></button>
              </>}
              {(h.status === 'approved' || h.status === 'rejected') && <>
                <span className="text-[11px] font-semibold capitalize mr-1" style={{ color: h.status === 'approved' ? '#3c7a2f' : '#53657d' }} data-testid="hours-status">{h.status}</span>
                <button onClick={() => act(h, 'pending')} data-testid="hours-to-pending-btn" title="Move back to Pending" className={`${icon} text-[#8a6a2c]`}><Undo2 size={15} /></button>
              </>}
              {h.status !== 'removed' ? <>
                <button onClick={() => setEditing(h.id)} data-testid="hours-edit-btn" title="Edit" className={`${icon} text-[#3B0A2E]`}><Pencil size={15} /></button>
                <button onClick={() => remove(h)} data-testid="hours-remove-btn" title="Remove" className={`${icon} text-red-500`}><Trash2 size={15} /></button>
              </> : <>
                <button onClick={() => act(h, 'restore')} data-testid="hours-restore-btn" title="Restore" className={`${icon} text-[#3c7a2f]`}><RotateCcw size={15} /></button>
                <button onClick={() => purge(h)} data-testid="hours-delete-forever-btn" className="ml-1 rounded-full px-3 py-1 text-[11.5px] font-semibold border border-red-200 text-red-600 hover:bg-red-50">Delete for good</button>
              </>}
            </td>
          </tr>
        )))}</tbody></table></div>
      )}
    </div>
  );
}
