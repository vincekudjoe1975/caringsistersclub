import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, Search, X, Repeat, Calendar, AlertTriangle, Tag, Save, HeartHandshake, ChevronUp, ChevronDown, ChevronsUpDown, Download, Mail, Send, Clock } from 'lucide-react';

const SortTh = ({ label, k, sort, onSort, align }) => {
  const active = sort.key === k;
  const Icon = !active ? ChevronsUpDown : (sort.dir === 'asc' ? ChevronUp : ChevronDown);
  return (
    <th className={`px-5 py-3 font-semibold ${align === 'right' ? 'text-right' : ''}`}>
      <button onClick={() => onSort(k)} data-testid={`sort-${k}`}
        className={`inline-flex items-center gap-1 uppercase tracking-wide hover:text-[#B4247E] transition-colors ${active ? 'text-[#B4247E]' : ''}`}>
        {label}<Icon size={13} className={active ? 'opacity-90' : 'opacity-40'} />
      </button>
    </th>
  );
};

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
  const [quickFilter, setQuickFilter] = useState('all'); // all | monthly | lapsed | major
  const [sort, setSort] = useState({ key: 'lifetime', dir: 'desc' });
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [noteDraft, setNoteDraft] = useState('');
  const [tagsDraft, setTagsDraft] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [sendingReactivation, setSendingReactivation] = useState(false);
  const [segModal, setSegModal] = useState(false);
  const [segSubject, setSegSubject] = useState('');
  const [segMessage, setSegMessage] = useState('');
  const [segSending, setSegSending] = useState(false);
  const [sendingTestCopy, setSendingTestCopy] = useState(false);
  const [appeals, setAppeals] = useState([]);
  const [showAppeals, setShowAppeals] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [scheduled, setScheduled] = useState([]);
  const [showScheduled, setShowScheduled] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduling, setScheduling] = useState(false);
  const [scheduleRepeat, setScheduleRepeat] = useState('none');

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

  const loadAppeals = useCallback(async () => {
    try {
      const { data } = await api.get('/admin/appeals');
      setAppeals(data.items || []);
    } catch (e) {
      console.error('AdminDonors: failed to load appeals', e);
    }
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const { data } = await api.get('/admin/appeal-templates');
      setTemplates(data.items || []);
    } catch (e) { console.error('AdminDonors: failed to load templates', e); }
  }, []);

  const loadScheduled = useCallback(async () => {
    try {
      const { data } = await api.get('/admin/scheduled-appeals');
      setScheduled(data.items || []);
    } catch (e) { console.error('AdminDonors: failed to load scheduled', e); }
  }, []);

  useEffect(() => { load(); loadAppeals(); loadTemplates(); loadScheduled(); }, [load, loadAppeals, loadTemplates, loadScheduled]);

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

  const sendReactivation = async () => {
    if (!selected?.email) return;
    const lastSent = detail?.reactivation_last_sent;
    const warn = lastSent
      ? `A "we miss you" email was already sent to this donor on ${dateStr(lastSent)}. Send another one to ${selected.email}?`
      : `Send a warm "we miss you" email to ${selected.email}?`;
    if (!window.confirm(warn)) return;
    setSendingReactivation(true);
    try {
      const { data } = await api.post(`/admin/donors/${encodeURIComponent(selected.email)}/reactivation`);
      if (data.sent) {
        toast({ title: 'Email sent', description: `"We miss you" note sent to ${data.email}.` });
        try {
          const { data: fresh } = await api.get(`/admin/donors/${encodeURIComponent(selected.email)}`);
          setDetail(fresh);
        } catch (e) { /* non-fatal: log refresh only */ }
      } else {
        toast({ title: 'Not delivered', description: data.detail || 'The provider could not deliver to that address.', variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSendingReactivation(false);
    }
  };

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

  const MAJOR_DONOR_MIN = 500;

  const matchesQuick = (d) => {
    if (quickFilter === 'monthly') return d.has_monthly;
    if (quickFilter === 'lapsed') return d.lapsed;
    if (quickFilter === 'major') return (d.lifetime || 0) >= MAJOR_DONOR_MIN;
    return true;
  };

  const toggleSort = (key) => {
    setSort((s) => s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: key === 'name' ? 'asc' : 'desc' });
  };

  const filtered = donors
    .filter((d) =>
      (!q || (d.name || '').toLowerCase().includes(q.toLowerCase()) || (d.email || '').toLowerCase().includes(q.toLowerCase()))
      && matchesQuick(d)
    )
    .sort((a, b) => {
      const dir = sort.dir === 'asc' ? 1 : -1;
      let av; let bv;
      if (sort.key === 'name') { av = (a.name || '').toLowerCase(); bv = (b.name || '').toLowerCase(); }
      else if (sort.key === 'gifts') { av = a.gifts || 0; bv = b.gifts || 0; }
      else if (sort.key === 'last_gift') { av = a.last_gift || ''; bv = b.last_gift || ''; }
      else { av = a.lifetime || 0; bv = b.lifetime || 0; }
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });

  const quickFilters = [
    { key: 'all', label: 'All', count: donors.length },
    { key: 'monthly', label: 'Monthly', count: donors.filter((d) => d.has_monthly).length },
    { key: 'lapsed', label: 'Lapsed', count: donors.filter((d) => d.lapsed).length },
    { key: 'major', label: `Major ($${MAJOR_DONOR_MIN}+)`, count: donors.filter((d) => (d.lifetime || 0) >= MAJOR_DONOR_MIN).length },
  ];

  const currentFilterLabel = quickFilters.find((f) => f.key === quickFilter)?.label || 'All';
  const segmentCount = quickFilters.find((f) => f.key === quickFilter)?.count || 0;

  const exportCsv = () => {
    const header = ['Name', 'Email', 'Gifts', 'Lifetime', 'Last Gift', 'Monthly', 'Lapsed', 'Tags'];
    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows = filtered.map((d) => [
      d.name, d.email, d.gifts, d.lifetime, d.last_gift ? new Date(d.last_gift).toISOString().slice(0, 10) : '',
      d.has_monthly ? 'Yes' : 'No', d.lapsed ? 'Yes' : 'No', (d.tags || []).join('; '),
    ].map(esc).join(','));
    const csv = [header.map(esc).join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `donors-${quickFilter}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const sendTestCopy = async () => {
    if (!segSubject.trim() || !segMessage.trim()) {
      toast({ title: 'Missing fields', description: 'Please add a subject and a message first.', variant: 'destructive' });
      return;
    }
    setSendingTestCopy(true);
    try {
      const { data } = await api.post('/admin/donors/segment-email/test', { segment: quickFilter, subject: segSubject, message: segMessage });
      if (data.sent) {
        toast({ title: 'Test copy sent', description: `Preview sent to ${data.to}.` });
      } else {
        toast({ title: 'Not delivered', description: data.detail || 'The provider could not deliver to your address.', variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSendingTestCopy(false);
    }
  };

  const sendSegmentEmail = async () => {
    if (!segSubject.trim() || !segMessage.trim()) {
      toast({ title: 'Missing fields', description: 'Please add a subject and a message.', variant: 'destructive' });
      return;
    }
    setSegSending(true);
    try {
      const { data } = await api.post('/admin/donors/segment-email', { segment: quickFilter, subject: segSubject, message: segMessage });
      toast({ title: 'Appeal sent', description: `Delivered to ${data.sent} of ${data.recipients} ${currentFilterLabel} donor${data.recipients === 1 ? '' : 's'}.` });
      setSegModal(false); setSegSubject(''); setSegMessage('');
      loadAppeals();
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSegSending(false);
    }
  };

  const applyTemplate = (id) => {
    const t = templates.find((x) => x.id === id);
    if (t) { setSegSubject(t.subject); setSegMessage(t.message); }
  };

  const saveTemplate = async () => {
    if (!segSubject.trim() || !segMessage.trim()) {
      toast({ title: 'Nothing to save', description: 'Add a subject and message first.', variant: 'destructive' });
      return;
    }
    const name = window.prompt('Name this template (e.g. "Year-End Appeal"):');
    if (!name || !name.trim()) return;
    try {
      await api.post('/admin/appeal-templates', { name: name.trim(), subject: segSubject, message: segMessage });
      toast({ title: 'Template saved', description: `"${name.trim()}" is ready to reuse.` });
      loadTemplates();
    } catch (e) {
      toast({ title: 'Save failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    }
  };

  const deleteTemplate = async (id) => {
    try { await api.delete(`/admin/appeal-templates/${id}`); loadTemplates(); }
    catch (e) { toast({ title: 'Delete failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' }); }
  };

  const scheduleAppeal = async () => {
    if (!segSubject.trim() || !segMessage.trim()) {
      toast({ title: 'Missing fields', description: 'Please add a subject and a message.', variant: 'destructive' });
      return;
    }
    if (!scheduleDate) {
      toast({ title: 'Pick a date', description: 'Choose a date to schedule this appeal.', variant: 'destructive' });
      return;
    }
    setScheduling(true);
    try {
      await api.post('/admin/scheduled-appeals', { segment: quickFilter, subject: segSubject, message: segMessage, send_on: scheduleDate, repeat: scheduleRepeat });
      toast({ title: 'Appeal scheduled', description: `Will send to ${currentFilterLabel} donors on ${new Date(scheduleDate).toLocaleDateString()}.` });
      setSegModal(false); setSegSubject(''); setSegMessage(''); setScheduleDate(''); setScheduleRepeat('none');
      loadScheduled();
    } catch (e) {
      toast({ title: 'Schedule failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setScheduling(false);
    }
  };

  const cancelScheduled = async (id) => {
    if (!window.confirm('Cancel this scheduled appeal?')) return;
    try { await api.delete(`/admin/scheduled-appeals/${id}`); loadScheduled(); }
    catch (e) { toast({ title: 'Cancel failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' }); }
  };

  const todayStr = new Date().toISOString().slice(0, 10);

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
          <button onClick={() => setQuickFilter((v) => v === 'lapsed' ? 'all' : 'lapsed')} data-testid="toggle-lapsed-filter"
            className="px-4 py-2 rounded-full text-[12.5px] font-semibold whitespace-nowrap text-white" style={{ background: '#e85c3a' }}>
            {quickFilter === 'lapsed' ? 'Show all donors' : 'Review lapsed'}
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex flex-wrap items-center gap-2 flex-1" data-testid="donor-quick-filters">
          {quickFilters.map((f) => (
            <button key={f.key} onClick={() => setQuickFilter(f.key)} data-testid={`donor-filter-${f.key}`}
              className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold transition-colors ${quickFilter === f.key ? 'bg-[#3B0A2E] text-white' : 'bg-white text-[#3B0A2E]'}`}
              style={quickFilter === f.key ? {} : { border: '1px solid rgba(59,10,46,0.15)' }}>
              {f.label} <span className="opacity-60">({f.count})</span>
            </button>
          ))}
        </div>
        <button onClick={exportCsv} disabled={filtered.length === 0} data-testid="donors-export-csv-btn"
          className="px-4 py-1.5 rounded-full text-[12.5px] font-semibold flex items-center gap-1.5 bg-white text-[#3B0A2E] disabled:opacity-50" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>
          <Download size={14} /> Export CSV
        </button>
        <button onClick={() => setSegModal(true)} disabled={segmentCount === 0} data-testid="donors-email-segment-btn"
          className="btn-magenta px-4 py-1.5 rounded-full text-[12.5px] font-semibold flex items-center gap-1.5 disabled:opacity-50">
          <Mail size={14} /> Email {currentFilterLabel} ({segmentCount})
        </button>
      </div>

      <div className="relative max-w-sm mb-6">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#241019]/40" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search donors by name or email"
          className="w-full rounded-full border border-[#3B0A2E]/15 pl-10 pr-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8"><p className="text-[#241019]/50">{quickFilter === 'all' && !q ? 'No donors yet.' : 'No donors match this filter.'}</p></div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide" style={{ background: '#faf2f7' }}>
                <SortTh label="Donor" k="name" sort={sort} onSort={toggleSort} />
                <SortTh label="Gifts" k="gifts" sort={sort} onSort={toggleSort} />
                <SortTh label="Last Gift" k="last_gift" sort={sort} onSort={toggleSort} />
                <SortTh label="Lifetime" k="lifetime" sort={sort} onSort={toggleSort} align="right" />
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

      <div className="mt-8">
        <button onClick={() => setShowAppeals((v) => !v)} data-testid="toggle-appeal-history"
          className="flex items-center gap-2 text-[13.5px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] transition-colors">
          <Clock size={15} /> Appeal History {appeals.length > 0 && <span className="opacity-60">({appeals.length})</span>}
          {showAppeals ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
        {showAppeals && (
          <div className="mt-3 bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden" data-testid="appeal-history-panel">
            {appeals.length === 0 ? (
              <p className="text-[#241019]/50 text-[13px] p-6 text-center">No segment appeals have been sent yet.</p>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide" style={{ background: '#faf2f7' }}>
                    <th className="px-5 py-3 font-semibold">Sent</th>
                    <th className="px-5 py-3 font-semibold">Segment</th>
                    <th className="px-5 py-3 font-semibold">Subject</th>
                    <th className="px-5 py-3 font-semibold">By</th>
                    <th className="px-5 py-3 font-semibold text-right">Delivered</th>
                    <th className="px-5 py-3 font-semibold text-right">Clicks</th>
                    <th className="px-5 py-3 font-semibold text-right">Gifts</th>
                    <th className="px-5 py-3 font-semibold text-right">Raised</th>
                  </tr>
                </thead>
                <tbody>
                  {appeals.map((a, i) => (
                    <tr key={i} className="border-t border-[#3B0A2E]/8 text-[13px]" data-testid="appeal-history-row">
                      <td className="px-5 py-3 text-[#241019]/70 whitespace-nowrap">{a.sent_at ? new Date(a.sent_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}</td>
                      <td className="px-5 py-3"><span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full capitalize" style={{ background: '#f2e6ee', color: '#B4247E' }}>{a.segment}</span></td>
                      <td className="px-5 py-3 text-[#3B0A2E] font-medium max-w-[220px] truncate">{a.subject}</td>
                      <td className="px-5 py-3 text-[#241019]/60">{a.sent_by_name || '—'}</td>
                      <td className="px-5 py-3 text-right text-[#3B0A2E] font-semibold">{a.sent} / {a.recipients}</td>
                      <td className="px-5 py-3 text-right text-[#241019]/70" data-testid="appeal-clicks">{a.clicks ?? 0}</td>
                      <td className="px-5 py-3 text-right text-[#241019]/70" data-testid="appeal-gifts">{a.donations ?? 0}</td>
                      <td className="px-5 py-3 text-right font-semibold" style={{ color: a.raised > 0 ? '#3c7a2f' : '#241019' }} data-testid="appeal-raised">${(a.raised || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      <div className="mt-4">
        <button onClick={() => setShowScheduled((v) => !v)} data-testid="toggle-scheduled-appeals"
          className="flex items-center gap-2 text-[13.5px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] transition-colors">
          <Clock size={15} /> Scheduled Appeals {scheduled.filter((s) => s.status === 'scheduled').length > 0 && <span className="opacity-60">({scheduled.filter((s) => s.status === 'scheduled').length})</span>}
          {showScheduled ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
        {showScheduled && (
          <div className="mt-3 bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden" data-testid="scheduled-appeals-panel">
            {scheduled.length === 0 ? (
              <p className="text-[#241019]/50 text-[13px] p-6 text-center">No scheduled appeals. Pick a date in the "Email" composer to schedule one.</p>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide" style={{ background: '#faf2f7' }}>
                    <th className="px-5 py-3 font-semibold">Next Send</th>
                    <th className="px-5 py-3 font-semibold">Repeats</th>
                    <th className="px-5 py-3 font-semibold">Segment</th>
                    <th className="px-5 py-3 font-semibold">Subject</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                    <th className="px-5 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {scheduled.map((s) => (
                    <tr key={s.id} className="border-t border-[#3B0A2E]/8 text-[13px]" data-testid="scheduled-appeal-row">
                      <td className="px-5 py-3 text-[#241019]/70 whitespace-nowrap">{s.send_on ? new Date(s.send_on).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}</td>
                      <td className="px-5 py-3 text-[#241019]/70 capitalize" data-testid="scheduled-repeat">{s.repeat && s.repeat !== 'none' ? <span className="flex items-center gap-1"><Repeat size={12} /> {s.repeat}{s.runs ? ` · ${s.runs} sent` : ''}</span> : 'Once'}</td>
                      <td className="px-5 py-3"><span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full capitalize" style={{ background: '#f2e6ee', color: '#B4247E' }}>{s.segment}</span></td>
                      <td className="px-5 py-3 text-[#3B0A2E] font-medium max-w-[200px] truncate">{s.subject}</td>
                      <td className="px-5 py-3">
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full capitalize" style={s.status === 'scheduled' ? { background: '#eef6ec', color: '#3c7a2f' } : s.status === 'sent' ? { background: '#eef1f5', color: '#53657d' } : { background: '#fdeae3', color: '#c1431f' }}>
                          {s.status === 'sent' && s.result ? `Sent (${s.result.sent}/${s.result.recipients})` : s.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right">
                        {s.status === 'scheduled' && (
                          <button onClick={() => cancelScheduled(s.id)} data-testid="cancel-scheduled-btn"
                            className="text-[12px] font-semibold text-[#c1431f] hover:underline">Cancel</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

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
                    <div className="rounded-xl p-4 mt-5" style={{ background: '#fdf1ed' }} data-testid="lapsed-detail-block">
                      <div className="flex items-center gap-2.5 mb-3">
                        <AlertTriangle size={16} className="text-[#c1431f] shrink-0" />
                        <p className="text-[12.5px] text-[#7a2f18]">This monthly donor hasn't had a recurring gift in over 35 days. Consider reaching out.</p>
                      </div>
                      <button onClick={sendReactivation} disabled={sendingReactivation || !selected?.email} data-testid="send-reactivation-btn"
                        className="rounded-full px-5 py-2.5 font-semibold text-[13px] flex items-center gap-2 text-white disabled:opacity-60" style={{ background: '#c1431f' }}>
                        {sendingReactivation ? <><Loader2 size={14} className="animate-spin" /> Sending…</> : <><HeartHandshake size={15} /> Send "We Miss You" Email</>}
                      </button>
                      {detail.reactivation_last_sent && (
                        <p className="text-[11.5px] text-[#7a2f18]/75 mt-2.5 flex items-center gap-1.5" data-testid="reactivation-last-sent">
                          <HeartHandshake size={12} /> Last "we miss you" email sent {dateStr(detail.reactivation_last_sent)}
                        </p>
                      )}
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

      {segModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(36,16,25,0.55)' }} onClick={() => !segSending && setSegModal(false)} data-testid="segment-email-modal">
          <div className="bg-white rounded-2xl w-full max-w-lg overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
              <h3 className="font-serif text-white text-[18px] font-semibold">Email {currentFilterLabel} Donors</h3>
              <button onClick={() => !segSending && setSegModal(false)} className="text-white/80 hover:text-white" data-testid="segment-modal-close"><X size={18} /></button>
            </div>
            <div className="p-6">
              <p className="text-[13px] text-[#241019]/60 mb-4">This appeal will be sent to <strong className="text-[#B4247E]">{segmentCount}</strong> {currentFilterLabel.toLowerCase()} donor{segmentCount === 1 ? '' : 's'} with an email on file, wrapped in your branded template with a "Make a Gift" button.</p>

              {templates.length > 0 && (
                <div className="mb-4">
                  <label className="text-[13px] font-semibold text-[#3B0A2E]">Load a saved template</label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {templates.map((t) => (
                      <span key={t.id} className="inline-flex items-center gap-1.5 text-[12px] font-semibold px-2.5 py-1 rounded-full" style={{ background: '#f2e6ee', color: '#B4247E' }}>
                        <button onClick={() => applyTemplate(t.id)} data-testid="apply-template" title="Use this template">{t.name}</button>
                        <button onClick={() => deleteTemplate(t.id)} data-testid="delete-template" title="Delete template" className="hover:text-[#c1431f]"><X size={11} /></button>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <label className="text-[13px] font-semibold text-[#3B0A2E]">Subject</label>
              <input value={segSubject} onChange={(e) => setSegSubject(e.target.value)} data-testid="segment-subject-input"
                placeholder="A heartfelt update from The Caring Sisters Club"
                className="w-full mt-1.5 mb-4 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              <label className="text-[13px] font-semibold text-[#3B0A2E]">Message</label>
              <textarea value={segMessage} onChange={(e) => setSegMessage(e.target.value)} rows={5} data-testid="segment-message-input"
                placeholder="Write a warm, personal appeal to this group of supporters…"
                className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E] resize-none" />

              <div className="flex flex-wrap items-end gap-3 mt-4 pt-4 border-t border-[#3B0A2E]/10">
                <button onClick={saveTemplate} data-testid="save-template-btn"
                  className="text-[12.5px] font-semibold text-[#3B0A2E] flex items-center gap-1.5 hover:text-[#B4247E]"><Save size={14} /> Save as template</button>
                <div className="flex-1" />
                <div>
                  <label className="text-[12px] font-semibold text-[#3B0A2E] block mb-1">Schedule for</label>
                  <input type="date" min={todayStr} value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)} data-testid="schedule-date-input"
                    className="rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13px] focus:outline-none focus:border-[#B4247E]" />
                </div>
                {scheduleDate && (
                  <div>
                    <label className="text-[12px] font-semibold text-[#3B0A2E] block mb-1">Repeat</label>
                    <select value={scheduleRepeat} onChange={(e) => setScheduleRepeat(e.target.value)} data-testid="schedule-repeat-select"
                      className="rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13px] bg-white focus:outline-none focus:border-[#B4247E]">
                      <option value="none">Does not repeat</option>
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap justify-end gap-2 mt-5">
                <button onClick={() => setSegModal(false)} disabled={segSending || sendingTestCopy || scheduling} className="px-5 py-2.5 rounded-full text-[13.5px] font-semibold bg-white text-[#3B0A2E]" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>Cancel</button>
                <button onClick={sendTestCopy} disabled={segSending || sendingTestCopy || scheduling} data-testid="segment-test-copy-btn"
                  className="px-5 py-2.5 rounded-full text-[13.5px] font-semibold bg-white text-[#B4247E] flex items-center gap-2 disabled:opacity-60" style={{ border: '1px solid rgba(180,36,126,0.4)' }}>
                  {sendingTestCopy ? <><Loader2 size={15} className="animate-spin" /> Sending…</> : <><Mail size={15} /> Test copy</>}
                </button>
                {scheduleDate ? (
                  <button onClick={scheduleAppeal} disabled={scheduling || segSending} data-testid="segment-schedule-btn"
                    className="btn-magenta px-6 py-2.5 rounded-full text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
                    {scheduling ? <><Loader2 size={15} className="animate-spin" /> Scheduling…</> : <><Clock size={15} /> Schedule</>}
                  </button>
                ) : (
                  <button onClick={sendSegmentEmail} disabled={segSending || sendingTestCopy} data-testid="segment-send-btn"
                    className="btn-magenta px-6 py-2.5 rounded-full text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
                    {segSending ? <><Loader2 size={15} className="animate-spin" /> Sending…</> : <><Send size={15} /> Send to {segmentCount}</>}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
