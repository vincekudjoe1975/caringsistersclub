import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Plus, Trash2, Square, Printer } from 'lucide-react';
import { Results } from '../Ballots';

const inputCls = 'w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';
const KIND = { resolution: 'Resolution', amendment: 'Bylaw amendment', election: 'Election' };
const local = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

function BallotForm({ onCreated }) {
  const { toast } = useToast();
  const now = new Date();
  const [f, setF] = useState({ kind: 'resolution', title: '', description: '', position: '', candidate_ids: [], opens_at: local(now), closes_at: local(new Date(now.getTime() + 7 * 864e5)) });
  const [cands, setCands] = useState([]);
  useEffect(() => { if (f.kind === 'election' && !cands.length) api.get('/admin/members/candidates').then(({ data }) => setCands(data)); }, [f.kind, cands.length]);
  const setKind = (kind) => {
    const opens = kind === 'amendment' ? new Date(now.getTime() + 10 * 864e5 + 36e5) : now;
    setF({ ...f, kind, opens_at: local(opens), closes_at: local(new Date(opens.getTime() + 7 * 864e5)) });
  };
  const toggle = (id) => setF({ ...f, candidate_ids: f.candidate_ids.includes(id) ? f.candidate_ids.filter((x) => x !== id) : [...f.candidate_ids, id] });
  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/members/ballots', { ...f, opens_at: new Date(f.opens_at).toISOString(), closes_at: new Date(f.closes_at).toISOString() });
      toast({ title: 'Ballot created', description: 'Notice emailed to all members.' }); setF({ ...f, title: '', description: '', candidate_ids: [] }); onCreated();
    } catch (ex) { toast({ title: 'Could not create ballot', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <form onSubmit={submit} data-testid="ballot-form" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 space-y-3 self-start">
      <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">New ballot</p>
      <div className="flex gap-1">{Object.entries(KIND).map(([k, l]) => <button type="button" key={k} data-testid={`ballot-kind-${k}`} onClick={() => setKind(k)} className={`flex-1 rounded-full py-1.5 text-[12.5px] font-semibold ${f.kind === k ? 'bg-[#3B0A2E] text-white' : 'bg-[#F7EFE9] text-[#3B0A2E]'}`}>{l}</button>)}</div>
      {f.kind === 'amendment' && <p className="text-[12px] text-[#B4247E]">Amendments need 10 days' written notice before voting opens and a two-thirds majority of members in good standing.</p>}
      <input data-testid="ballot-title" placeholder="Title" required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inputCls} />
      <textarea data-testid="ballot-description" rows={3} placeholder={f.kind === 'amendment' ? 'Exact proposed bylaw wording' : 'Details'} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className={inputCls} />
      {f.kind === 'election' && (
        <>
          <input data-testid="ballot-position" placeholder="Position (e.g. President)" value={f.position} onChange={(e) => setF({ ...f, position: e.target.value })} className={inputCls} />
          <div className="max-h-44 overflow-auto border border-[#3B0A2E]/10 rounded-lg p-2">
            {cands.map((c) => (
              <label key={c.user_id} className={`flex items-center gap-2 text-[13px] py-1 ${c.eligible ? '' : 'opacity-50'}`}>
                <input data-testid={`cand-${c.user_id}`} type="checkbox" disabled={!c.eligible} checked={f.candidate_ids.includes(c.user_id)} onChange={() => toggle(c.user_id)} className="accent-[#B4247E]" />
                {c.name}{!c.eligible && <span className="text-[11px]">({c.reason})</span>}
              </label>
            ))}
            {!cands.length && <p className="text-[12.5px] text-[#241019]/50">No members yet.</p>}
          </div>
        </>
      )}
      <div className="grid grid-cols-2 gap-2 text-[12px] text-[#241019]/60">
        <label>Opens<input data-testid="ballot-opens" type="datetime-local" value={f.opens_at} onChange={(e) => setF({ ...f, opens_at: e.target.value })} className={inputCls} /></label>
        <label>Closes<input data-testid="ballot-closes" type="datetime-local" value={f.closes_at} onChange={(e) => setF({ ...f, closes_at: e.target.value })} className={inputCls} /></label>
      </div>
      <button data-testid="ballot-create-btn" className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold flex items-center gap-1"><Plus size={14} /> Create & notify members</button>
    </form>
  );
}

export function AdminBallots() {
  const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const load = useCallback(() => api.get('/admin/members/ballots').then(({ data }) => setRows(data)), []);
  useEffect(() => { load(); }, [load]);
  const del = async (id) => { try { await api.delete(`/admin/members/ballots/${id}`); load(); } catch (ex) { toast({ title: 'Cannot delete', description: ex?.response?.data?.detail, variant: 'destructive' }); } };
  return (
    <div className="grid lg:grid-cols-[1fr_1.3fr] gap-6" data-testid="admin-ballots">
      <BallotForm onCreated={load} />
      <div className="space-y-3">
        {rows.map((b) => (
          <div key={b.id} data-testid={`admin-ballot-${b.id}`} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
            <div className="flex justify-between gap-3">
              <div><p className="text-[12px] text-[#B4247E] font-semibold">{KIND[b.kind]}{b.position ? `: ${b.position}` : ''} · {b.state}</p><p className="font-semibold text-[#3B0A2E]">{b.title}</p></div>
              <span className="flex gap-3 shrink-0">
                {b.state === 'closed' && <a href={`/vote-record/${b.id}`} target="_blank" rel="noreferrer" data-testid={`ballot-record-${b.id}`} className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Printer size={12} /> Official record</a>}
                {b.state === 'open' && <button data-testid={`ballot-close-${b.id}`} onClick={async () => { if (window.confirm('Close voting now?')) { await api.post(`/admin/members/ballots/${b.id}/close`); load(); } }} className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Square size={12} /> Close now</button>}
                <button data-testid={`ballot-del-${b.id}`} onClick={() => del(b.id)} className="text-[#241019]/35 hover:text-red-600"><Trash2 size={14} /></button>
              </span>
            </div>
            <Results b={b} />
            {b.state !== 'closed' && <p className="text-[11.5px] text-[#241019]/45 mt-1">Live totals (staff only). Votes are secret: individual choices are never stored with a name.</p>}
          </div>
        ))}
        {!rows.length && <p className="text-[13.5px] text-[#241019]/50">No ballots yet.</p>}
      </div>
    </div>
  );
}
