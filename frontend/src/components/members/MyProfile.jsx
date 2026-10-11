import React, { useState } from 'react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { Loader2, Save, Camera } from 'lucide-react';
import { Avatar } from './Avatar';
import { LeaveRequest } from './LeaveRequest';
import { CheckinCode } from './Phase6';

const inputCls = 'w-full mt-1.5 rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';

const MONTHS = Array.from({ length: 12 }, (_, i) => new Date(2000, i, 1).toLocaleString(undefined, { month: 'long' }));

export function MyProfile({ me, onChange }) {
  const { toast } = useToast();
  const [p, setP] = useState({ city: '', phone: '', bio: '', show_contact: false, prayer_weekly: true, ...me.profile });
  const [busy, setBusy] = useState(false);
  const [pic, setPic] = useState(false);
  const set = (k, v) => setP((s) => ({ ...s, [k]: v }));
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file); setPic(true);
    try { await api.post('/members/photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); toast({ title: 'Photo updated' }); onChange(); }
    catch (ex) { toast({ title: 'Upload failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setPic(false); }
  };
  const removePic = async () => { await api.delete('/members/photo'); toast({ title: 'Photo removed' }); onChange(); };
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
        <div><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{me.name}</p><p className="text-[13px] text-[#241019]/55">{me.email}</p>
          <div className="flex items-center gap-3 mt-1.5">
            <label data-testid="profile-photo-upload" className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1 cursor-pointer">{pic ? <Loader2 size={12} className="animate-spin" /> : <Camera size={12} />} {me.picture ? 'Change photo' : 'Add a photo'}
              <input data-testid="profile-photo-input" type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files?.[0])} /></label>
            {me.picture && <button type="button" data-testid="profile-photo-remove" onClick={removePic} className="text-[12.5px] text-[#241019]/50 hover:text-red-600">Remove</button>}
          </div>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">City</label><input data-testid="profile-city" value={p.city} onChange={(e) => set('city', e.target.value)} className={inputCls} /></div>
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Phone</label><input data-testid="profile-phone" value={p.phone} onChange={(e) => set('phone', e.target.value)} className={inputCls} /></div>
      </div>
      <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">Birthday (month & day only)</label>
        <div className="flex gap-2 mt-1.5">
          <select data-testid="profile-bday-month" value={p.birthday_month || ''} onChange={(e) => set('birthday_month', e.target.value ? Number(e.target.value) : null)} className={`${inputCls} mt-0`}>
            <option value="">Month</option>{MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
          <select data-testid="profile-bday-day" value={p.birthday_day || ''} onChange={(e) => set('birthday_day', e.target.value ? Number(e.target.value) : null)} className={`${inputCls} mt-0 w-28`}>
            <option value="">Day</option>{Array.from({ length: 31 }, (_, i) => <option key={i} value={i + 1}>{i + 1}</option>)}
          </select>
        </div>
      </div>
      <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">A little about you</label><textarea data-testid="profile-bio" rows={4} value={p.bio} onChange={(e) => set('bio', e.target.value)} className={inputCls} /></div>
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-5 cursor-pointer">
        <input data-testid="profile-show-contact" type="checkbox" checked={p.show_contact} onChange={(e) => set('show_contact', e.target.checked)} className="mt-1 accent-[#B4247E] w-4 h-4" />
        <span>Show my email and phone to other members in the directory</span>
      </label>
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-3 cursor-pointer">
        <input data-testid="profile-prayer-weekly" type="checkbox" checked={p.prayer_weekly !== false} onChange={(e) => set('prayer_weekly', e.target.checked)} className="mt-1 accent-[#B4247E] w-4 h-4" />
        <span>Email me a weekly digest of new prayer requests and praise reports</span>
      </label>
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-3 cursor-pointer">
        <input data-testid="profile-bday-notices" type="checkbox" checked={p.bday_notices !== false} onChange={(e) => set('bday_notices', e.target.checked)} className="mt-1 accent-[#B4247E] w-4 h-4" />
        <span>Email me when it's a sister's birthday so I can send wishes</span>
      </label>
      <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 mt-3 cursor-pointer">
        <input data-testid="profile-bday-card" type="checkbox" checked={p.bday_card !== false} onChange={(e) => set('bday_card', e.target.checked)} className="mt-1 accent-[#B4247E] w-4 h-4" />
        <span>Send me a birthday card email from the Club on my birthday</span>
      </label>
      <button data-testid="profile-save-btn" disabled={busy} className="btn-magenta rounded-full px-7 py-3 font-semibold mt-7 flex items-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Save profile
      </button>
    <CheckinCode />
    <LeaveRequest me={me} onChange={onChange} />
    </form>
  );
}
