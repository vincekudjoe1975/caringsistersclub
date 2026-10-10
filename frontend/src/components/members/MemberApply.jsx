import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { Loader2, Send } from 'lucide-react';

const inputCls = 'w-full mt-1.5 rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';

const Check = ({ id, checked, onChange, children }) => (
  <label className="flex items-start gap-3 text-[14px] text-[#241019]/80 cursor-pointer">
    <input data-testid={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-1 accent-[#B4247E] w-4 h-4" />
    <span>{children}</span>
  </label>
);

export function MemberApply({ me, onDone }) {
  const [f, setF] = useState({ phone: '', city: '', referred_by: '', why: '', is_adult: false, is_delaware: false, agrees_bylaws: false });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    try { await api.post('/members/apply', f); onDone(); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Something went wrong. Please try again.'); }
    finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} data-testid="member-apply-form" className="bg-white rounded-3xl p-8 md:p-10 max-w-2xl mx-auto" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
      <p className="eyebrow text-[#B4247E] mb-2">Membership application</p>
      <h1 className="font-serif text-[30px] text-[#3B0A2E] font-semibold mb-2">Join the sisterhood, {(me.name || '').split(' ')[0]}</h1>
      <p className="text-[#241019]/65 text-[14.5px] mb-7">Membership is by referral from a current member. Once approved, you'll get full access to the member portal. <Link to="/membership" className="text-[#B4247E] font-semibold">See requirements</Link></p>
      <div className="grid sm:grid-cols-2 gap-4">
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">City / town in Delaware *</label><input data-testid="apply-city" value={f.city} onChange={(e) => set('city')(e.target.value)} className={inputCls} /></div>
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Phone</label><input data-testid="apply-phone" value={f.phone} onChange={(e) => set('phone')(e.target.value)} className={inputCls} /></div>
      </div>
      <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">Referring member (full name) *</label><input data-testid="apply-referred" value={f.referred_by} onChange={(e) => set('referred_by')(e.target.value)} className={inputCls} /></div>
      <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">Why would you like to join?</label><textarea data-testid="apply-why" rows={3} value={f.why} onChange={(e) => set('why')(e.target.value)} className={inputCls} /></div>
      <div className="space-y-3 mt-6">
        <Check id="apply-adult" checked={f.is_adult} onChange={set('is_adult')}>I am a woman aged 18 or older.</Check>
        <Check id="apply-delaware" checked={f.is_delaware} onChange={set('is_delaware')}>I live in the State of Delaware.</Check>
        <Check id="apply-bylaws" checked={f.agrees_bylaws} onChange={set('agrees_bylaws')}>I agree to uphold the Club's bylaws, including the $10 registration fee and $10 monthly dues.</Check>
      </div>
      {err && <p data-testid="apply-error" className="text-red-600 text-[13.5px] mt-5">{err}</p>}
      <button data-testid="apply-submit-btn" disabled={busy} className="btn-magenta rounded-full px-8 py-3.5 font-semibold mt-7 flex items-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />} Submit application
      </button>
    </form>
  );
}
