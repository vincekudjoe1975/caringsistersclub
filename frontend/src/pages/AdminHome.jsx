import React, { useEffect, useState } from 'react';
import * as Icons from 'lucide-react';
import { Loader2, Plus, Trash2, Save, UploadCloud, ArrowUp, ArrowDown, LayoutTemplate, MessageSquareQuote, Target } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { imgSrc, uploadImage, resetHomeContentCache, DEFAULT_MISSION_IMAGE } from '../lib/useHomeContent';

const ICONS = ['Briefcase', 'HeartHandshake', 'Home', 'Users', 'GraduationCap', 'Sparkles', 'HandHeart', 'Globe', 'Heart', 'Star', 'Crown', 'Sprout'];
const inp = 'w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E] bg-white';
const Label = ({ children }) => <label className="text-[12px] font-semibold text-[#3B0A2E] block mb-1 mt-3">{children}</label>;

export function ImageUpload({ value, onChange, category, testid, fallback, round }) {
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  const pick = async (file) => {
    if (!file) return;
    setBusy(true);
    try { onChange(await uploadImage(file, category)); }
    catch (err) { toast({ title: 'Upload failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const src = imgSrc(value, fallback);
  return (
    <div className="flex items-center gap-3">
      {src ? <img src={src} alt="" className={`${round ? 'w-12 h-12 rounded-full' : 'w-24 h-16 rounded-lg'} object-cover border border-[#3B0A2E]/10`} />
        : <span className={`${round ? 'w-12 h-12 rounded-full' : 'w-24 h-16 rounded-lg'} bg-[#faf2f7] border border-[#3B0A2E]/10`} />}
      <label className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1.5 cursor-pointer">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <UploadCloud size={14} />} {value ? 'Replace' : 'Upload'}
        <input type="file" accept="image/*" className="hidden" data-testid={testid} onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ''; }} />
      </label>
      {value && <button type="button" onClick={() => onChange('')} className="text-[12px] text-[#241019]/50 hover:text-red-600">Remove</button>}
    </div>
  );
}

export function TestimonialsEditor({ items, onChange, max, prefix }) {
  const upd = (i, patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  const move = (i, d) => { const n = [...items]; [n[i], n[i + d]] = [n[i + d], n[i]]; onChange(n); };
  return (
    <div className="space-y-3">
      {items.map((t, i) => (
        <div key={t.id || i} className="rounded-xl p-4 border border-[#3B0A2E]/10" data-testid={`${prefix}-testimonial-row`}>
          <textarea rows={2} value={t.quote} onChange={(e) => upd(i, { quote: e.target.value })} placeholder="Quote" className={`${inp} resize-y`} data-testid={`${prefix}-testimonial-quote-${i}`} />
          <div className="grid sm:grid-cols-2 gap-2 mt-2">
            <input value={t.name} onChange={(e) => upd(i, { name: e.target.value })} placeholder="Name" className={inp} data-testid={`${prefix}-testimonial-name-${i}`} />
            <input value={t.role} onChange={(e) => upd(i, { role: e.target.value })} placeholder="Role (e.g. Member since 2022)" className={inp} data-testid={`${prefix}-testimonial-role-${i}`} />
          </div>
          <div className="flex items-center justify-between mt-3">
            <ImageUpload value={t.photo_url} onChange={(url) => upd(i, { photo_url: url })} category="gallery" testid={`${prefix}-testimonial-photo-${i}`} round />
            <div className="flex">
              <button type="button" disabled={i === 0} onClick={() => move(i, -1)} className="p-1.5 disabled:opacity-25"><ArrowUp size={14} /></button>
              <button type="button" disabled={i === items.length - 1} onClick={() => move(i, 1)} className="p-1.5 disabled:opacity-25"><ArrowDown size={14} /></button>
              <button type="button" onClick={() => onChange(items.filter((_, j) => j !== i))} className="p-1.5 text-red-500" data-testid={`${prefix}-testimonial-del-${i}`}><Trash2 size={14} /></button>
            </div>
          </div>
        </div>
      ))}
      {items.length < max && (
        <button type="button" onClick={() => onChange([...items, { quote: '', name: '', role: '', photo_url: '' }])} data-testid={`${prefix}-add-testimonial-btn`}
          className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Plus size={14} /> Add testimonial</button>
      )}
    </div>
  );
}

function Card({ icon: Icon, title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-2"><Icon size={18} className="text-[#B4247E]" /> {title}</h3>
      {children}
    </div>
  );
}

function PillarsEditor({ items, onChange }) {
  const upd = (i, patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  return (
    <div className="space-y-3">
      {items.map((p, i) => {
        const Icon = Icons[p.icon] || Icons.Sparkles;
        return (
          <div key={i} className="rounded-xl p-4 border border-[#3B0A2E]/10" data-testid="home-pillar-row">
            <div className="flex gap-2 items-center">
              <span className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><Icon size={17} className="text-white" /></span>
              <select value={p.icon} onChange={(e) => upd(i, { icon: e.target.value })} className={`${inp} w-40`} data-testid={`home-pillar-icon-${i}`}>{ICONS.map((n) => <option key={n} value={n}>{n}</option>)}</select>
              <input value={p.title} onChange={(e) => upd(i, { title: e.target.value })} placeholder="Title" className={inp} data-testid={`home-pillar-title-${i}`} />
              {items.length > 1 && <button type="button" onClick={() => onChange(items.filter((_, j) => j !== i))} className="p-2 text-red-500" data-testid={`home-pillar-del-${i}`}><Trash2 size={15} /></button>}
            </div>
            <textarea rows={2} value={p.text} onChange={(e) => upd(i, { text: e.target.value })} className={`${inp} mt-2 resize-y`} data-testid={`home-pillar-text-${i}`} />
            <div className="grid grid-cols-2 gap-2 mt-2">
              <input value={p.cta} onChange={(e) => upd(i, { cta: e.target.value })} placeholder="Button text" className={inp} data-testid={`home-pillar-cta-${i}`} />
              <input value={p.to} onChange={(e) => upd(i, { to: e.target.value })} placeholder="/initiatives" className={inp} data-testid={`home-pillar-link-${i}`} />
            </div>
          </div>
        );
      })}
      {items.length < 6 && <button type="button" onClick={() => onChange([...items, { icon: 'Sparkles', title: '', text: '', cta: 'Learn More', to: '/initiatives' }])} data-testid="home-add-pillar-btn" className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Plus size={14} /> Add card</button>}
    </div>
  );
}

export default function AdminHome() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  useEffect(() => {
    api.get('/home-content').then(({ data }) => setForm(data)).catch(() => toast({ title: 'Could not load Home content', variant: 'destructive' }));
  }, [toast]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/admin/home-content', form);
      setForm(data); resetHomeContentCache();
      toast({ title: 'Home page published', description: 'Your changes are live.' });
    } catch (err) {
      toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setSaving(false); }
  };

  if (!form) return <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={30} /></div>;
  return (
    <div data-testid="admin-home">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold flex items-center gap-2"><LayoutTemplate size={22} className="text-[#B4247E]" /> Home Page</h2>
          <p className="text-[#241019]/60 text-[13.5px]" data-testid="home-status">{form.updated_at ? `Last published ${new Date(form.updated_at).toLocaleString()}` : 'Showing the original content. Edit and publish to make it yours.'}</p>
        </div>
        <button onClick={save} disabled={saving} data-testid="save-home-btn" className="btn-magenta rounded-full px-6 py-2.5 text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Publish Changes
        </button>
      </div>
      <div className="grid xl:grid-cols-2 gap-5 items-start">
        <div className="space-y-5">
          <Card icon={Target} title="Mission section">
            <Label>Small heading</Label><input value={form.mission_heading} onChange={set('mission_heading')} className={inp} data-testid="home-mission-heading-input" />
            <Label>Title</Label><input value={form.mission_title} onChange={set('mission_title')} className={inp} data-testid="home-mission-title-input" />
            <Label>Paragraph</Label><textarea rows={5} value={form.mission_body} onChange={set('mission_body')} className={`${inp} resize-y`} data-testid="home-mission-body-input" />
            <Label>Highlighted quote (optional)</Label><input value={form.mission_quote} onChange={set('mission_quote')} className={inp} data-testid="home-mission-quote-input" />
            <Label>Photo</Label><ImageUpload value={form.mission_image} onChange={(url) => setForm((f) => ({ ...f, mission_image: url }))} category="gallery" testid="home-mission-image-input" fallback={DEFAULT_MISSION_IMAGE} />
          </Card>
          <Card icon={LayoutTemplate} title="Mission cards"><PillarsEditor items={form.pillars} onChange={(pillars) => setForm({ ...form, pillars })} /></Card>
        </div>
        <Card icon={MessageSquareQuote} title="Testimonials">
          <p className="text-[12.5px] text-[#241019]/55 mb-3">Shown on the Home page. You can also feature any of these on a program page.</p>
          <TestimonialsEditor items={form.testimonials} onChange={(testimonials) => setForm({ ...form, testimonials })} max={12} prefix="home" />
        </Card>
      </div>
    </div>
  );
}
