import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, Search, X, Repeat, Calendar, AlertTriangle, Tag, Save } from 'lucide-react';

function fmt(n) {
  return `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
}
function dateStr(iso) {
  return iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
}

export default function AdminDonors() {
  const { toast } = useToast();
  const [donors, setDonors] = useState([]);
  const [lapsedCount, setLapsedCount] = useState(0);
  const [showLapsedOnly, setShowLapsedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [noteDraft, setNoteDraft] = useState('');
  const [tagsDraft, setTagsDraft] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/admin/donors');
      setDonors(data.donors || []);
      setLapsedCount(data.lapsed_count || 0);
    } catch (e) {
      console.error('AdminDonors: failed to load', e);
      setDonors([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openDonor = async (d) => {
    if (!d.email) return;
    setSelected(d);
    setDetail(null);
    setDetailLoading(true);
    try {
      const { data } = await api.get(`/admin/donors/${encodeURIComponent(d.email)}`);
      setDetail(data);
      setNoteDraft(data.note || '');
      setTagsDraft(data.tags || []);
      setTagInput('');
    } catch (e) {
      console.error('AdminDonors: detail failed', e);
    } finally {
      setDetailLoading(false);
    }
  };

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tagsDraft.includes(t)) setTagsDraft([...tagsDraft, t]);
    setTagInput('');
  };

  const removeTag = (t) => setTagsDraft(tagsDraft.filter((x) => x !== t));

  const saveNotes = async () => {
    if (!selected?.email) return;
    setSavingNotes(true);
    try {
      await api.put(`/admin/donors/${encodeURIComponent(selected.email)}/notes`, { note: noteDraft, tags: tagsDraft });
      toast({ title: 'Saved', description: 'Donor notes and tags updated.' });
      load();
    } catch (e) {
      toast({ title: 'Save failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSavingNotes(false);
    }
  };

  const filtered = donors.filter((d) =>
    (!q || (d.name || '').toLowerCase().includes(q.toLowerCase()) || (d.email || '').toLowerCase().includes(q.toLowerCase()))
    && (!showLapsedOnly || d.lapsed)
  );

  if (loading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;
  }

  return (
    <div>
      {lapsedCount > 0 && (
        <div className="flex items-center justify-between gap-3 rounded-2xl p-4 mb-5 border" style={{ background: '#fdf1ed', borderColor: '#e8b4a0' }} data-testid="lapsed-alert-banner">
          <div className="flex items-center gap-3">
            <span className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: '#e85c3a' }}>
              <AlertTriangle size={17} className="text-white" />
            </span>
            <p className="text-[13.5px] text-[#7a2f18]">
              <strong>{lapsedCount} monthly donor{lapsedCount > 1 ? 's have' : ' has'}</strong> no recurring gift in over 35 days — their monthly support may have lapsed.
            </p>
          </div>
          <button onClick={() => setShowLapsedOnly((v) => !v)} data-testid="toggle-lapsed-filter"
            className="px-4 py-2 rounded-full text-[12.5px] font-semibold whitespace-nowrap text-white" style={{ background: '#e85c3a' }}>
            {showLapsedOnly ? 'Show all donors' : 'Review lapsed'}
          </button>
        </div>
      )}

      <div className="relative max-w-sm mb-6">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#241019]/40" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search donors by name or email"
          className="w-full rounded-full border border-[#3B0A2E]/15 pl-10 pr-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8"><p className="text-[#241019]/50">{showLapsedOnly ? 'No lapsed donors.' : 'No donors yet.'}</p></div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide" style={{ background: '#faf2f7' }}>
                <th className="px-5 py-3 font-semibold">Donor</th>
                <th className="px-5 py-3 font-semibold">Gifts</th>
                <th className="px-5 py-3 font-semibold">Last Gift</th>
                <th className="px-5 py-3 font-semibold text-right">Lifetime</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d, i) => (
                <tr key={d.email || i} onClick={() => openDonor(d)} data-testid="donor-row"
                  className={`border-t border-[#3B0A2E]/8 text-[13.5px] ${d.email ? 'cursor-pointer hover:bg-[#faf2f7]' : ''}`}>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <span className="w-8 h-8 rounded-full flex items-center justify-center text-white text-[12px] font-serif font-bold" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
                        {(d.name || '?').charAt(0)}
                      </span>
                      <div>
                        <p className="text-[#3B0A2E] font-semibold flex items-center gap-1.5 flex-wrap">
                          {d.name}
                          {d.has_monthly && <Repeat size={12} className="text-[#B4247E]" title="Monthly donor" />}
                          {d.lapsed && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1" style={{ background: '#fdeae3', color: '#c1431f' }} data-testid="lapsed-badge">
                              <AlertTriangle size={9} /> LAPSED
                            </span>
                          )}
                          {(d.tags || []).slice(0, 3).map((t) => (
                            <span key={t} className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: '#eef1f5', color: '#53657d' }}>{t}</span>
                          ))}
                        </p>
                        <p className="text-[#241019]/50 text-[12px]">{d.email || 'no email'}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-[#241019]/70">{d.gifts}</td>
                  <td className="px-5 py-3 text-[#241019]/70">{dateStr(d.last_gift)}</td>
                  <td className="px-5 py-3 text-right font-semibold text-[#3B0A2E]">{fmt(d.lifetime)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={() => setSelected(null)}>
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 flex items-start justify-between" style={{ background: '#faf2f7' }}>
              <div>
                <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{selected.name}</h3>
                <p className="text-[#241019]/55 text-[13px]">{selected.email}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-[#241019]/50 hover:text-[#3B0A2E]"><X size={20} /></button>
            </div>
            <div className="p-6">
              {detailLoading ? (
                <div className="flex justify-center py-10"><Loader2 className="animate-spin text-[#B4247E]" size={28} /></div>
              ) : detail ? (
                <>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="rounded-xl p-4" style={{ background: '#faf2f7' }}>
                      <p className="font-serif text-[24px] text-[#3B0A2E] font-bold leading-none">{fmt(detail.lifetime)}</p>
                      <p className="text-[#241019]/55 text-[12px] mt-1">Lifetime giving</p>
                    </div>
                    <div className="rounded-xl p-4" style={{ background: '#faf2f7' }}>
                      <p className="font-serif text-[24px] text-[#3B0A2E] font-bold leading-none">{detail.gift_count}</p>
                      <p className="text-[#241019]/55 text-[12px] mt-1">Total gifts</p>
                    </div>
                  </div>
                  <h4 className="eyebrow text-[#B4247E] mb-3">Giving History</h4>
                  <ul className="space-y-2.5">
                    {detail.gifts.map((g) => (
                      <li key={g.session_id} className="flex items-center justify-between text-[13.5px] pb-2.5 border-b border-[#3B0A2E]/8 last:border-0">
                        <span className="flex items-center gap-2 text-[#241019]/70"><Calendar size={13} className="text-[#CBA24B]" /> {dateStr(g.updated_at)}</span>
                        <span className="flex items-center gap-3">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full" style={g.frequency === 'monthly' ? { background: '#f2e6ee', color: '#B4247E' } : { background: '#f0ece4', color: '#8a6d2f' }}>
                            {g.frequency === 'monthly' ? (g.is_renewal ? 'Renewal' : 'Monthly') : 'One-Time'}
                          </span>
                          <span className="font-semibold text-[#3B0A2E]">${Number(g.amount).toLocaleString()}</span>
                        </span>
                      </li>
                    ))}
                  </ul>

                  {detail.lapsed && (
                    <div className="flex items-center gap-2.5 rounded-xl p-3 mt-5" style={{ background: '#fdf1ed' }}>
                      <AlertTriangle size={16} className="text-[#c1431f] shrink-0" />
                      <p className="text-[12.5px] text-[#7a2f18]">This monthly donor hasn't had a recurring gift in over 35 days. Consider reaching out.</p>
                    </div>
                  )}

                  <div className="mt-6 pt-5 border-t border-[#3B0A2E]/10">
                    <h4 className="eyebrow text-[#B4247E] mb-3 flex items-center gap-1.5"><Tag size={13} /> Private Staff Notes</h4>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {tagsDraft.map((t) => (
                        <span key={t} className="text-[12px] font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5" style={{ background: '#eef1f5', color: '#53657d' }}>
                          {t}
                          <button onClick={() => removeTag(t)} className="hover:text-[#c1431f]" data-testid="remove-tag"><X size={11} /></button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2 mb-3">
                      <input value={tagInput} onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
                        placeholder="Add a tag (e.g. Major Donor, Board Contact)" data-testid="tag-input"
                        className="flex-1 rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13px] focus:outline-none focus:border-[#B4247E]" />
                      <button onClick={addTag} className="px-3 py-2 rounded-lg text-[13px] font-semibold bg-white text-[#3B0A2E]" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>Add</button>
                    </div>
                    <textarea value={noteDraft} onChange={(e) => setNoteDraft(e.target.value)} rows={4} data-testid="donor-note-input"
                      placeholder="Private notes only visible to staff — e.g. relationship history, preferences, outreach plans."
                      className="w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2.5 text-[13.5px] focus:outline-none focus:border-[#B4247E] resize-none" />
                    <button onClick={saveNotes} disabled={savingNotes} data-testid="save-notes-btn"
                      className="btn-magenta rounded-full px-5 py-2.5 font-semibold text-[13.5px] mt-3 flex items-center gap-2 disabled:opacity-60">
                      {savingNotes ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : <><Save size={14} /> Save Notes</>}
                    </button>
                  </div>
                </>
              ) : (
                <p className="text-[#241019]/50 text-center py-6">Could not load details.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
