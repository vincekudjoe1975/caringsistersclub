import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { resetTransparencyCache } from '../lib/useTransparency';
import { useToast } from '../hooks/use-toast';
import { Loader2, Plus, Trash2, Save, UploadCloud, FileText, PieChart, Sparkles, BarChart3, ExternalLink } from 'lucide-react';

const COLORS = [
  { v: 'var(--csc-magenta)', n: 'Magenta' }, { v: 'var(--csc-plum-soft)', n: 'Plum' }, { v: 'var(--csc-gold)', n: 'Gold' },
  { v: '#3B0A2E', n: 'Deep plum' }, { v: '#D14FA0', n: 'Pink' }, { v: '#8a6a2c', n: 'Bronze' },
];
const TYPES = [{ v: '990', n: 'Form 990' }, { v: 'annual', n: 'Annual Report' }, { v: 'audit', n: 'Audit' }, { v: 'other', n: 'Other' }];
const inp = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E] bg-white';
const thisYear = String(new Date().getFullYear());

function Card({ icon: Icon, title, hint, onAdd, addLabel, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Icon size={18} className="text-[#B4247E]" /> {title}</h3>
          {hint && <p className="text-[12.5px] text-[#241019]/55 mt-0.5">{hint}</p>}
        </div>
        {onAdd && <button type="button" onClick={onAdd} className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1 shrink-0" data-testid={`add-${addLabel}-btn`}><Plus size={14} /> Add</button>}
      </div>
      <div className="space-y-2.5">{children}</div>
    </div>
  );
}

const DelBtn = ({ onClick, id }) => <button type="button" onClick={onClick} data-testid={id} className="p-2 text-red-500 hover:text-red-700 shrink-0"><Trash2 size={15} /></button>;

function useList(form, setForm, key) {
  const upd = (i, patch) => setForm({ ...form, [key]: form[key].map((x, j) => (j === i ? { ...x, ...patch } : x)) });
  const del = (i) => setForm({ ...form, [key]: form[key].filter((_, j) => j !== i) });
  const add = (item) => setForm({ ...form, [key]: [...form[key], item] });
  return { upd, del, add };
}

function Breakdown({ form, setForm }) {
  const { upd, del, add } = useList(form, setForm, 'breakdown');
  const total = form.breakdown.reduce((s, b) => s + (Number(b.pct) || 0), 0);
  return (
    <Card icon={PieChart} title="How your gift is used" hint="Percentages must total 100%. The first row drives the big '¢ of every dollar' figure." onAdd={() => add({ label: '', pct: 0, color: 'var(--csc-gold)' })} addLabel="spend">
      {form.breakdown.map((b, i) => (
        <div key={i} className="flex gap-2 items-center" data-testid="spend-row">
          <input value={b.label} onChange={(e) => upd(i, { label: e.target.value })} placeholder="Category" className={`${inp} flex-1`} data-testid={`spend-label-${i}`} />
          <input type="number" min={0} max={100} step="0.1" value={b.pct} onChange={(e) => upd(i, { pct: e.target.value })} className={`${inp} w-24`} data-testid={`spend-pct-${i}`} />
          <select value={b.color} onChange={(e) => upd(i, { color: e.target.value })} className={`${inp} w-28`}>{COLORS.map((c) => <option key={c.v} value={c.v}>{c.n}</option>)}</select>
          <span className="w-4 h-4 rounded-full shrink-0" style={{ background: b.color }} />
          <DelBtn onClick={() => del(i)} id={`spend-del-${i}`} />
        </div>
      ))}
      <p className={`text-[12.5px] font-semibold ${Math.abs(total - 100) < 0.5 ? 'text-[#3c7a2f]' : 'text-red-600'}`} data-testid="spend-total">Total: {total.toFixed(1)}%</p>
      <div>
        <label className="text-[12px] font-semibold text-[#3B0A2E]">Headline text</label>
        <input value={form.headline_text} onChange={(e) => setForm({ ...form, headline_text: e.target.value })} className={`${inp} w-full mt-1`} data-testid="headline-text-input" />
      </div>
    </Card>
  );
}

function Stats({ form, setForm }) {
  const { upd, del, add } = useList(form, setForm, 'stats');
  return (
    <Card icon={Sparkles} title="Impact stats" hint="Shown on the Home page and Transparency page (first three)." onAdd={() => add({ value: '', label: '' })} addLabel="stat">
      {form.stats.map((s, i) => (
        <div key={i} className="flex gap-2 items-center" data-testid="stat-row">
          <input value={s.value} onChange={(e) => upd(i, { value: e.target.value })} placeholder="2,400+" className={`${inp} w-28`} data-testid={`stat-value-${i}`} />
          <input value={s.label} onChange={(e) => upd(i, { label: e.target.value })} placeholder="Sisters in our network" className={`${inp} flex-1`} data-testid={`stat-label-${i}`} />
          <DelBtn onClick={() => del(i)} id={`stat-del-${i}`} />
        </div>
      ))}
    </Card>
  );
}

function Financials({ form, setForm }) {
  const { upd, del, add } = useList(form, setForm, 'financials');
  return (
    <Card icon={BarChart3} title="Yearly financials" hint="Revenue, total expenses and program spending per fiscal year." onAdd={() => add({ year: thisYear, revenue: 0, expenses: 0, program_expenses: 0 })} addLabel="financial">
      {form.financials.length > 0 && <div className="grid grid-cols-[80px_1fr_1fr_1fr_36px] gap-2 text-[11px] uppercase tracking-wide text-[#241019]/50 font-semibold"><span>Year</span><span>Revenue $</span><span>Expenses $</span><span>Programs $</span><span /></div>}
      {form.financials.map((f, i) => (
        <div key={i} className="grid grid-cols-[80px_1fr_1fr_1fr_36px] gap-2 items-center" data-testid="financial-row">
          <input value={f.year} onChange={(e) => upd(i, { year: e.target.value })} className={inp} data-testid={`fin-year-${i}`} />
          {['revenue', 'expenses', 'program_expenses'].map((k) => (
            <input key={k} type="number" min={0} value={f[k]} onChange={(e) => upd(i, { [k]: e.target.value })} className={inp} data-testid={`fin-${k}-${i}`} />
          ))}
          <DelBtn onClick={() => del(i)} id={`fin-del-${i}`} />
        </div>
      ))}
    </Card>
  );
}

function Reports({ form, setForm }) {
  const { upd, del, add } = useList(form, setForm, 'reports');
  const [uploading, setUploading] = useState(false);
  const { toast } = useToast();
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file); fd.append('category', 'report'); fd.append('title', file.name);
    setUploading(true);
    try {
      const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      const kb = file.size / 1024;
      add({ year: thisYear, type: 'annual', title: '', url: data.url, size: kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB` });
    } catch (err) {
      toast({ title: 'Upload failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setUploading(false); }
  };
  return (
    <Card icon={FileText} title="Published reports" hint="Upload a PDF, then set its year and type. Blank titles use a standard name like “Form 990 — Fiscal Year 2025”.">
      {form.reports.map((r, i) => (
        <div key={r.id || i} className="flex flex-wrap gap-2 items-center" data-testid="report-row">
          <input value={r.year} onChange={(e) => upd(i, { year: e.target.value })} className={`${inp} w-20`} data-testid={`report-year-${i}`} />
          <select value={r.type} onChange={(e) => upd(i, { type: e.target.value })} className={`${inp} w-36`} data-testid={`report-type-${i}`}>{TYPES.map((t) => <option key={t.v} value={t.v}>{t.n}</option>)}</select>
          <input value={r.title} onChange={(e) => upd(i, { title: e.target.value })} placeholder="Title (optional)" className={`${inp} flex-1 min-w-[160px]`} data-testid={`report-title-${i}`} />
          <a href={r.url.startsWith('/api/') ? `${process.env.REACT_APP_BACKEND_URL}${r.url}` : r.url} target="_blank" rel="noreferrer" className="p-2 text-[#3B0A2E] hover:text-[#B4247E]"><ExternalLink size={15} /></a>
          <DelBtn onClick={() => del(i)} id={`report-del-${i}`} />
        </div>
      ))}
      <label className="inline-flex items-center gap-2 text-[13px] font-semibold text-[#B4247E] cursor-pointer mt-1">
        {uploading ? <Loader2 size={15} className="animate-spin" /> : <UploadCloud size={15} />} Upload report (PDF)
        <input type="file" accept="application/pdf,.pdf" className="hidden" data-testid="report-upload-input" onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ''; }} />
      </label>
    </Card>
  );
}

export default function AdminTransparency() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const { toast } = useToast();

  useEffect(() => {
    api.get('/transparency').then(({ data }) => { setForm(data); setUpdatedAt(data.updated_at); })
      .catch(() => toast({ title: 'Could not load transparency data', variant: 'destructive' }));
  }, [toast]);

  const save = async () => {
    setSaving(true);
    try {
      const num = (v) => Number(v) || 0;
      const body = {
        ...form,
        breakdown: form.breakdown.map((b) => ({ ...b, pct: num(b.pct) })),
        financials: form.financials.map((f) => ({ ...f, revenue: num(f.revenue), expenses: num(f.expenses), program_expenses: num(f.program_expenses) })),
      };
      const { data } = await api.put('/admin/transparency', body);
      setForm(data); setUpdatedAt(data.updated_at); resetTransparencyCache();
      toast({ title: 'Transparency page published', description: 'Your changes are live.' });
    } catch (err) {
      toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setSaving(false); }
  };

  if (!form) return <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={30} /></div>;
  return (
    <div data-testid="admin-transparency">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">Transparency</h2>
          <p className="text-[#241019]/60 text-[13.5px]" data-testid="transparency-status">
            {updatedAt ? `Last published ${new Date(updatedAt).toLocaleString()}` : 'Not yet published — the public page shows illustrative figures until you save.'}
          </p>
        </div>
        <button onClick={save} disabled={saving} data-testid="save-transparency-btn" className="btn-magenta rounded-full px-6 py-2.5 text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Publish Changes
        </button>
      </div>
      <div className="grid xl:grid-cols-2 gap-5">
        <Breakdown form={form} setForm={setForm} />
        <Stats form={form} setForm={setForm} />
        <Financials form={form} setForm={setForm} />
        <Reports form={form} setForm={setForm} />
      </div>
    </div>
  );
}
