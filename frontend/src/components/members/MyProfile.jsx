import React, { useState } from 'react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { Loader2, Save } from 'lucide-react';
import { Avatar } from './Avatar';

const inputCls = 'w-full mt-1.5 rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';

export function MyProfile({ me, onChange }) {
  const { toast } = useToast();
  const [p, setP] = useState({ city: '', phone: '', bio: '', show_contact: false, ...me.profile });
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setP((s) => ({ ...s, [k]: v }));
  const save = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await api.put('/members/profile', p); toast({ title: 'Profile saved' }); onChange(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <form onSubmit={save} data-testid="profile-form" className="max-w-xl">
      <div className="flex items-center gap-4 mb-7">
        <Avatar name={me.name} src={me.picture} size={64} />
        <div><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{me.name}</p><p className="text-[13px] text-[#241019]/55">{me.email}</p></div>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">City</label><input data-testid="profile-city" value={p.city} onChange={(e) => set('city', e.target.value)} className={inputCls} /></div>
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Phone</label><input data-testid="profile-phone" value={p.phone} onChange={(e) => set('phone', e.target.value)} className={inputCls} /></div>
      </div>
      <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">A little about you</label><textarea data-testid="profile-bio" rows={4} value={p.bio} onChange={(e) => set('bio', e.target.value)} className={inputCls} /></div>
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-5 cursor-pointer">
        <input data-testid="profile-show-contact" type="checkbox" checked={p.show_contact} onChange={(e) => set('show_contact', e.target.checked)} className="mt-1 accent-[#B4247E] w-4 h-4" />
        <span>Show my email and phone to other members in the directory</span>
      </label>
      <button data-testid="profile-save-btn" disabled={busy} className="btn-magenta rounded-full px-7 py-3 font-semibold mt-7 flex items-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Save profile
      </button>
    </form>
  );
}
