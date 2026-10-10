import React, { useEffect, useState } from 'react';
import * as Icons from 'lucide-react';
import { Loader2, Save, Plus, Trash2, ArrowUp, ArrowDown, Info, Gem, History } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { ImageUpload } from './AdminHome';
import { resetAboutCache } from '../lib/useHomeContent';
import { mission } from '../mock/mock';

const ICONS = ['Heart', 'Shield', 'Sparkles', 'Users', 'HandHeart', 'Star', 'Crown', 'Globe', 'Sprout', 'GraduationCap', 'Briefcase', 'HeartHandshake'];
const inp = 'w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E] bg-white';
const Label = ({ children }) => <label className="text-[12px] font-semibold text-[#3B0A2E] block mb-1 mt-3">{children}</label>;
const Card = ({ icon: Icon, title, children }) => (
  <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6">
    <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-2"><Icon size={18} className="text-[#B4247E]" /> {title}</h3>
    {children}
  </div>
);

function useListOps(list, setList) {
  return {
    upd: (i, patch) => setList(list.map((x, j) => (j === i ? { ...x, ...patch } : x))),
    del: (i) => setList(list.filter((_, j) => j !== i)),
    move: (i, d) => { const n = [...list]; [n[i], n[i + d]] = [n[i + d], n[i]]; setList(n); },
  };
}

function RowTools({ i, len, ops, testid }) {
  return (
    <div className="flex shrink-0">
      <button type="button" disabled={i === 0} onClick={() => ops.move(i, -1)} className="p-1.5 disabled:opacity-25"><ArrowUp size={14} /></button>
      <button type="button" disabled={i === len - 1} onClick={() => ops.move(i, 1)} className="p-1.5 disabled:opacity-25"><ArrowDown size={14} /></button>
      <button type="button" onClick={() => ops.del(i)} className="p-1.5 text-red-500" data-testid={`${testid}-del-${i}`}><Trash2 size={14} /></button>
    </div>
  );
}

function ValuesEditor({ items, onChange }) {
  const ops = useListOps(items, onChange);
  return (
    <div className="space-y-3">
      {items.map((v, i) => {
        const Icon = Icons[v.icon] || Icons.Heart;
        return (
          <div key={i} className="rounded-xl p-3 border border-[#3B0A2E]/10" data-testid="about-value-row">
            <div className="flex gap-2 items-center">
              <span className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><Icon size={15} className="text-white" /></span>
              <select value={v.icon} onChange={(e) => ops.upd(i, { icon: e.target.value })} className={`${inp} w-36`}>{ICONS.map((n) => <option key={n}>{n}</option>)}</select>
              <input value={v.title} onChange={(e) => ops.upd(i, { title: e.target.value })} placeholder="Value" className={inp} data-testid={`about-value-title-${i}`} />
              <RowTools i={i} len={items.length} ops={ops} testid="about-value" />
            </div>
            <textarea rows={2} value={v.text} onChange={(e) => ops.upd(i, { text: e.target.value })} className={`${inp} mt-2 resize-y`} data-testid={`about-value-text-${i}`} />
          </div>
        );
      })}
      {items.length < 8 && <button type="button" onClick={() => onChange([...items, { icon: 'Heart', title: '', text: '' }])} data-testid="about-add-value-btn" className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Plus size={14} /> Add value</button>}
    </div>
  );
}

function StoryEditor({ items, onChange }) {
  const ops = useListOps(items, onChange);
  return (
    <div className="space-y-3">
      {items.map((s, i) => (
        <div key={i} className="rounded-xl p-3 border border-[#3B0A2E]/10" data-testid="about-story-row">
          <div className="flex gap-2 items-center">
            <input value={s.year} onChange={(e) => ops.upd(i, { year: e.target.value })} placeholder="Year" className={`${inp} w-24`} data-testid={`about-story-year-${i}`} />
            <input value={s.title} onChange={(e) => ops.upd(i, { title: e.target.value })} placeholder="Milestone" className={inp} data-testid={`about-story-title-${i}`} />
            <RowTools i={i} len={items.length} ops={ops} testid="about-story" />
          </div>
          <textarea rows={2} value={s.text} onChange={(e) => ops.upd(i, { text: e.target.value })} className={`${inp} mt-2 resize-y`} data-testid={`about-story-text-${i}`} />
          <div className="mt-2"><ImageUpload value={s.image} onChange={(url) => ops.upd(i, { image: url })} category="gallery" testid={`about-story-image-${i}`} /></div>
        </div>
      ))}
      {items.length < 12 && <button type="button" onClick={() => onChange([...items, { year: '', title: '', text: '', image: '' }])} data-testid="about-add-story-btn" className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><Plus size={14} /> Add milestone</button>}
    </div>
  );
}

export default function AdminAbout() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();
  useEffect(() => { api.get('/about-content').then(({ data }) => setForm(data)).catch(() => toast({ title: 'Could not load About content', variant: 'destructive' })); }, [toast]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async () => {
    setSaving(true);
    try { const { data } = await api.put('/admin/about-content', form); setForm(data); resetAboutCache(); toast({ title: 'About page published', description: 'Your changes are live.' }); }
    catch (err) { toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' }); }
    finally { setSaving(false); }
  };
  if (!form) return <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={30} /></div>;
  return (
    <div data-testid="admin-about">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">About Page</h2>
          <p className="text-[#241019]/60 text-[13.5px]" data-testid="about-status">{form.updated_at ? `Last published ${new Date(form.updated_at).toLocaleString()}` : 'Showing the original content. Edit and publish to make it yours.'}</p>
        </div>
        <button onClick={save} disabled={saving} data-testid="save-about-btn" className="btn-magenta rounded-full px-6 py-2.5 text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Publish Changes
        </button>
      </div>
      <div className="grid xl:grid-cols-2 gap-5 items-start">
        <div className="space-y-5">
          <Card icon={Info} title="Intro & mission">
            <Label>Page intro (under the title)</Label><textarea rows={2} value={form.hero_subtitle} onChange={set('hero_subtitle')} className={`${inp} resize-y`} data-testid="about-hero-input" />
            <Label>Mission title</Label><input value={form.mission_title} onChange={set('mission_title')} className={inp} data-testid="about-mission-title-input" />
            <Label>Mission paragraph</Label><textarea rows={5} value={form.mission_body} onChange={set('mission_body')} className={`${inp} resize-y`} data-testid="about-mission-body-input" />
            <Label>Mission photo</Label><ImageUpload value={form.mission_image} onChange={(url) => setForm((f) => ({ ...f, mission_image: url }))} category="gallery" testid="about-mission-image-input" fallback={mission.image} />
          </Card>
          <Card icon={Gem} title="Values"><ValuesEditor items={form.values} onChange={(values) => setForm({ ...form, values })} /></Card>
        </div>
        <Card icon={History} title="Our story">
          <Label>Section title</Label><input value={form.story_title} onChange={set('story_title')} className={`${inp} mb-3`} data-testid="about-story-section-title-input" />
          <StoryEditor items={form.story} onChange={(story) => setForm({ ...form, story })} />
        </Card>
      </div>
    </div>
  );
}
