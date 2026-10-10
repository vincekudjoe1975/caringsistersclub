import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { eventImg } from './Events';
import { TestimonialsEditor } from './AdminHome';
import { useSignupReport, Trend } from './AdminReports';
import { uploadImage, imgSrc } from '../lib/useHomeContent';
import { Loader2, Plus, Pencil, Trash2, ArrowUp, ArrowDown, Eye, EyeOff, X, UploadCloud, Tags, ExternalLink } from 'lucide-react';

const EMPTY = { title: '', category: '', image_url: '', summary: '', body: '', goals: [], impact: [], cta_text: 'Get Involved', cta_link: '/volunteer', published: true, gallery: [], testimonials: [], home_testimonial_ids: [], capacity: 0, waitlist_mode: 'claim' };
const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E] bg-white';
const Field = ({ label, children }) => <div><label className="text-[13px] font-semibold text-[#3B0A2E]">{label}</label>{children}</div>;

function ImageField({ value, onChange, title }) {
  const [uploading, setUploading] = useState(false);
  const { toast } = useToast();
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file); fd.append('category', 'program'); fd.append('title', title || file.name);
    setUploading(true);
    try { const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); onChange(data.url); }
    catch (err) { toast({ title: 'Image upload failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' }); }
    finally { setUploading(false); }
  };
  return (
    <div className="flex items-center gap-4">
      <img src={eventImg(value)} alt="" className="w-28 h-20 rounded-lg object-cover border border-[#3B0A2E]/10" />
      <label className="text-[13px] font-semibold text-[#B4247E] flex items-center gap-2 cursor-pointer">
        {uploading ? <Loader2 size={15} className="animate-spin" /> : <UploadCloud size={15} />} {value ? 'Replace image' : 'Upload image'}
        <input type="file" accept="image/*" className="hidden" data-testid="program-image-input" onChange={(e) => upload(e.target.files?.[0])} />
      </label>
    </div>
  );
}

function ProgramForm({ initial, categories, onClose, onSaved }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial });
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const setImpact = (i, patch) => setForm({ ...form, impact: form.impact.map((x, j) => (j === i ? { ...x, ...patch } : x)) });

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const body = { ...form, goals: (typeof form.goals === 'string' ? form.goals.split('\n') : form.goals) };
      if (initial.id) await api.put(`/admin/programs/${initial.id}`, body);
      else await api.post('/admin/programs', body);
      toast({ title: initial.id ? 'Program updated' : 'Program created', description: form.published ? 'It is live on the Initiatives page.' : 'Saved as hidden.' });
      onSaved();
    } catch (err) {
      toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={onClose}>
      <form onSubmit={save} onClick={(e) => e.stopPropagation()} data-testid="program-form" className="bg-white rounded-2xl max-w-3xl w-full max-h-[92vh] overflow-y-auto p-7 space-y-4">
        <div className="flex items-start justify-between">
          <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{initial.id ? 'Edit program' : 'New program'}</h3>
          <button type="button" onClick={onClose} className="text-[#241019]/50 hover:text-[#3B0A2E]"><X size={20} /></button>
        </div>
        <div className="grid sm:grid-cols-[2fr_1fr] gap-4">
          <Field label="Title *"><input required value={form.title} onChange={set('title')} data-testid="program-title-input" className={input} /></Field>
          <Field label="Category">
            <select value={form.category} onChange={set('category')} data-testid="program-category-select" className={input}>
              <option value="">None</option>
              {[...categories, ...(form.category && !categories.includes(form.category) ? [form.category] : [])].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
        </div>
        <ImageField value={form.image_url} title={form.title} onChange={(url) => setForm((f) => ({ ...f, image_url: url }))} />
        <Field label="Short description (shown on the card)"><textarea rows={2} value={form.summary} onChange={set('summary')} data-testid="program-summary-input" className={`${input} resize-none`} /></Field>
        <Field label="Full story (program detail page)"><textarea rows={6} value={form.body} onChange={set('body')} data-testid="program-body-input" className={`${input} resize-y`} /></Field>
        <Field label="Goals (one per line)">
          <textarea rows={3} value={Array.isArray(form.goals) ? form.goals.join('\n') : form.goals} onChange={(e) => setForm({ ...form, goals: e.target.value })} data-testid="program-goals-input" className={`${input} resize-y`} />
        </Field>
        <div>
          <div className="flex items-center justify-between">
            <label className="text-[13px] font-semibold text-[#3B0A2E]">Impact numbers</label>
            {form.impact.length < 6 && <button type="button" onClick={() => setForm({ ...form, impact: [...form.impact, { value: '', label: '' }] })} data-testid="program-add-impact-btn" className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Plus size={13} /> Add</button>}
          </div>
          {form.impact.map((s, i) => (
            <div key={i} className="flex gap-2 mt-2">
              <input value={s.value} onChange={(e) => setImpact(i, { value: e.target.value })} placeholder="120+" className={`${input} !mt-0 w-28`} data-testid={`program-impact-value-${i}`} />
              <input value={s.label} onChange={(e) => setImpact(i, { label: e.target.value })} placeholder="Women mentored" className={`${input} !mt-0 flex-1`} data-testid={`program-impact-label-${i}`} />
              <button type="button" onClick={() => setForm({ ...form, impact: form.impact.filter((_, j) => j !== i) })} className="p-2 text-red-500"><Trash2 size={15} /></button>
            </div>
          ))}
        </div>
        <GalleryEditor items={form.gallery || []} onChange={(gallery) => setForm((f) => ({ ...f, gallery }))} />
        <div>
          <label className="text-[13px] font-semibold text-[#3B0A2E] block mb-2">Member testimonials</label>
          <TestimonialsEditor items={form.testimonials || []} onChange={(testimonials) => setForm((f) => ({ ...f, testimonials }))} max={6} prefix="program" />
          <HomePicks selected={form.home_testimonial_ids || []} onChange={(ids) => setForm((f) => ({ ...f, home_testimonial_ids: ids }))} />
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Button text"><input value={form.cta_text} onChange={set('cta_text')} data-testid="program-cta-text-input" className={input} /></Field>
          <Field label="Button link (e.g. /volunteer, /donate or https://…)"><input value={form.cta_link} onChange={set('cta_link')} data-testid="program-cta-link-input" className={input} /></Field>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Seat limit (0 = unlimited). When full, new sign-ups join a waitlist.">
            <input type="number" min="0" value={form.capacity || 0} onChange={(e) => setForm({ ...form, capacity: Math.max(0, parseInt(e.target.value || '0', 10)) })} data-testid="program-capacity-input" className={input} />
          </Field>
          <Field label="When a seat opens up">
            <select value={form.waitlist_mode || 'claim'} onChange={set('waitlist_mode')} data-testid="program-waitlist-mode-select" className={input}>
              <option value="claim">Email next in line a 48-hour claim link</option>
              <option value="auto">Move next in line in automatically</option>
              <option value="broadcast">Email everyone waiting, first to claim wins</option>
            </select>
          </Field>
        </div>
        <label className="flex items-center gap-2 text-[13.5px] text-[#3B0A2E] font-semibold">
          <input type="checkbox" checked={form.published} onChange={(e) => setForm({ ...form, published: e.target.checked })} data-testid="program-published-checkbox" className="accent-[#B4247E] w-4 h-4" /> Published (visible on the website)
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-full text-[13.5px] font-semibold text-[#3B0A2E]" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>Cancel</button>
          <button type="submit" disabled={saving} data-testid="program-save-btn" className="btn-magenta px-6 py-2.5 rounded-full text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
            {saving && <Loader2 size={15} className="animate-spin" />} {initial.id ? 'Save changes' : 'Create program'}
          </button>
        </div>
      </form>
    </div>
  );
}

function GalleryEditor({ items, onChange }) {
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  const add = async (files) => {
    const list = Array.from(files || []).slice(0, 24 - items.length);
    if (!list.length) return;
    setBusy(true);
    const urls = [];
    for (const file of list) {
      try { urls.push(await uploadImage(file, 'program')); }
      catch (err) { toast({ title: `Upload failed: ${file.name}`, description: err?.response?.data?.detail || 'Try again', variant: 'destructive' }); }
    }
    onChange([...items, ...urls.map((url) => ({ url, caption: '' }))]);
    setBusy(false);
  };
  return (
    <div data-testid="program-gallery-editor">
      <label className="text-[13px] font-semibold text-[#3B0A2E] block mb-2">Photo gallery ({items.length}/24)</label>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {items.map((g, i) => (
          <div key={g.url} className="relative" data-testid="program-gallery-item">
            <img src={imgSrc(g.url)} alt="" className="w-full h-24 rounded-lg object-cover" />
            <button type="button" onClick={() => onChange(items.filter((_, j) => j !== i))} data-testid={`program-gallery-del-${i}`}
              className="absolute top-1 right-1 w-6 h-6 rounded-full bg-white/90 text-red-500 flex items-center justify-center"><X size={13} /></button>
            <input value={g.caption} onChange={(e) => onChange(items.map((x, j) => (j === i ? { ...x, caption: e.target.value } : x)))}
              placeholder="Caption" className="w-full mt-1 rounded border border-[#3B0A2E]/15 px-2 py-1 text-[12px]" data-testid={`program-gallery-caption-${i}`} />
          </div>
        ))}
        {items.length < 24 && (
          <label className="h-24 rounded-lg border-2 border-dashed border-[#3B0A2E]/15 flex flex-col items-center justify-center text-[12px] font-semibold text-[#B4247E] cursor-pointer hover:bg-[#faf2f7]">
            {busy ? <Loader2 size={18} className="animate-spin" /> : <UploadCloud size={18} />} Add photos
            <input type="file" accept="image/*" multiple className="hidden" data-testid="program-gallery-input" onChange={(e) => { add(e.target.files); e.target.value = ''; }} />
          </label>
        )}
      </div>
    </div>
  );
}

function HomePicks({ selected, onChange }) {
  const [list, setList] = useState([]);
  useEffect(() => { api.get('/home-content').then(({ data }) => setList(data.testimonials || [])).catch(() => {}); }, []);
  if (!list.length) return null;
  const toggle = (id) => onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id].slice(0, 6));
  return (
    <div className="mt-4 rounded-xl p-4" style={{ background: '#faf2f7' }} data-testid="program-home-picks">
      <p className="text-[12.5px] font-semibold text-[#3B0A2E] mb-2">Also feature testimonials from the Home page</p>
      <div className="space-y-1.5">
        {list.map((t) => (
          <label key={t.id} className="flex items-start gap-2 text-[12.5px] text-[#241019]/80 cursor-pointer">
            <input type="checkbox" checked={selected.includes(t.id)} onChange={() => toggle(t.id)} className="accent-[#B4247E] mt-0.5" data-testid={`program-home-pick-${t.id}`} />
            <span><strong>{t.name}</strong>: &ldquo;{t.quote.slice(0, 80)}{t.quote.length > 80 ? '…' : ''}&rdquo;</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function SignupCard() {
  const data = useSignupReport(2);
  if (!data || !data.rows.length) return null;
  const top = [...data.rows].sort((a, b) => b.counts[1] - a.counts[1]).slice(0, 4);
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-5 mb-5" data-testid="program-signup-card">
      <p className="text-[13px] font-semibold text-[#3B0A2E] mb-3">Sign-ups this month <span className="font-normal text-[#241019]/55">(vs last month · full report in Reports)</span></p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {top.map((r) => (
          <div key={r.program} className="rounded-xl px-4 py-3" style={{ background: '#faf2f7' }} data-testid="program-signup-card-item">
            <p className="text-[12px] text-[#241019]/60 truncate">{r.program}</p>
            <p className="font-serif text-[22px] font-bold text-[#3B0A2E] flex items-center gap-2">{r.counts[1]} <Trend t={r.trend} /><span className="text-[11px] font-sans font-normal text-[#241019]/45">was {r.counts[0]}</span></p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CategoryEditor({ categories, onSaved }) {
  const [text, setText] = useState(categories.join(', '));
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  useEffect(() => setText(categories.join(', ')), [categories]);
  const save = async () => {
    setSaving(true);
    try { const { data } = await api.put('/admin/program-categories', { categories: text.split(',') }); onSaved(data.categories); toast({ title: 'Categories saved' }); }
    catch (err) { toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' }); }
    finally { setSaving(false); }
  };
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-5 mb-5 flex flex-col sm:flex-row gap-3 sm:items-end" data-testid="program-categories-editor">
      <div className="flex-1">
        <label className="text-[13px] font-semibold text-[#3B0A2E] flex items-center gap-2"><Tags size={15} className="text-[#B4247E]" /> Filter categories (comma-separated, in display order)</label>
        <input value={text} onChange={(e) => setText(e.target.value)} data-testid="program-categories-input" className={input} />
      </div>
      <button onClick={save} disabled={saving} data-testid="program-categories-save-btn" className="rounded-full px-5 py-2.5 text-[13px] font-semibold text-[#3B0A2E] flex items-center gap-2" style={{ border: '1px solid rgba(59,10,46,0.18)' }}>
        {saving && <Loader2 size={14} className="animate-spin" />} Save Categories
      </button>
    </div>
  );
}

function ProgramRow({ p, first, last, onMove, onEdit, onToggle, onDelete }) {
  const iconBtn = 'p-2 text-[#3B0A2E] hover:text-[#B4247E] disabled:opacity-25';
  return (
    <div className={`bg-white rounded-2xl border border-[#3B0A2E]/8 p-4 flex flex-col sm:flex-row gap-4 sm:items-center ${p.published ? '' : 'opacity-60'}`} data-testid="admin-program-row">
      <div className="flex sm:flex-col">
        <button onClick={() => onMove(-1)} disabled={first} className={iconBtn} data-testid="program-move-up-btn"><ArrowUp size={15} /></button>
        <button onClick={() => onMove(1)} disabled={last} className={iconBtn} data-testid="program-move-down-btn"><ArrowDown size={15} /></button>
      </div>
      <img src={eventImg(p.image_url)} alt="" className="w-full sm:w-28 h-20 rounded-xl object-cover" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-serif text-[18px] text-[#3B0A2E] font-semibold truncate" data-testid="admin-program-title">{p.title}</h4>
          {!p.published && <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-[#eef1f5] text-[#53657d]">Hidden</span>}
          {p.capacity > 0 && <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-[#faf2f7] text-[#B4247E]" data-testid="admin-program-seats">{p.capacity - p.seats_left}/{p.capacity} seats{p.full ? ' · full' : ''}</span>}
        </div>
        <p className="text-[12.5px] text-[#241019]/60 truncate">{p.category || 'No category'} &middot; {p.summary}</p>
      </div>
      <div className="flex items-center gap-1">
        {p.published && <a href={`/initiatives/${p.slug}`} target="_blank" rel="noreferrer" className={iconBtn} title="View"><ExternalLink size={16} /></a>}
        <button onClick={onToggle} className={iconBtn} title={p.published ? 'Unpublish' : 'Publish'} data-testid="program-toggle-publish-btn">{p.published ? <EyeOff size={16} /> : <Eye size={16} />}</button>
        <button onClick={onEdit} className={iconBtn} data-testid="program-edit-btn"><Pencil size={16} /></button>
        <button onClick={onDelete} className="p-2 text-red-500 hover:text-red-700" data-testid="program-delete-btn"><Trash2 size={16} /></button>
      </div>
    </div>
  );
}

export default function AdminPrograms() {
  const [items, setItems] = useState(null);
  const [categories, setCategories] = useState([]);
  const [editing, setEditing] = useState(null);
  const { toast } = useToast();

  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/programs'); setItems(data.items || []); setCategories(data.categories || []); }
    catch (e) { console.error('AdminPrograms: load failed', e); setItems([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const move = async (i, dir) => {
    const next = [...items];
    [next[i], next[i + dir]] = [next[i + dir], next[i]];
    setItems(next);
    try { await api.post('/admin/programs/reorder', { ids: next.map((p) => p.id) }); }
    catch { toast({ title: 'Reorder failed', variant: 'destructive' }); load(); }
  };
  const toggle = async (p) => {
    try { await api.put(`/admin/programs/${p.id}`, { ...p, published: !p.published }); load(); toast({ title: p.published ? 'Program hidden' : 'Program published' }); }
    catch (err) { toast({ title: 'Update failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.title}"? This cannot be undone.`)) return;
    try { await api.delete(`/admin/programs/${p.id}`); toast({ title: 'Program deleted' }); load(); }
    catch { toast({ title: 'Delete failed', variant: 'destructive' }); }
  };

  return (
    <div data-testid="admin-programs">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">Programs & Initiatives</h2>
          <p className="text-[#241019]/60 text-[13.5px]">Published programs appear on the Initiatives page in this order, each with its own detail page.</p>
        </div>
        <button onClick={() => setEditing({})} data-testid="new-program-btn" className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2"><Plus size={16} /> New Program</button>
      </div>
      <SignupCard />
      <CategoryEditor categories={categories} onSaved={setCategories} />
      {items === null ? <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={30} /></div> : (
        <div className="space-y-3">{items.map((p, i) => (
          <ProgramRow key={p.id} p={p} first={i === 0} last={i === items.length - 1} onMove={(d) => move(i, d)}
            onEdit={() => setEditing(p)} onToggle={() => toggle(p)} onDelete={() => remove(p)} />
        ))}</div>
      )}
      {editing && <ProgramForm initial={editing} categories={categories} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}
