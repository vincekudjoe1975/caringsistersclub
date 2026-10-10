import React, { useState } from 'react';
import { Loader2, CheckCircle2, UserPlus, Users, Hourglass } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from '../pages/Events';

const inp = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E] bg-white';

export const SeatsBadge = ({ p, className = '' }) => {
  if (!p.capacity) return null;
  return p.full ? (
    <span className={`inline-flex items-center gap-1 text-[11.5px] font-semibold px-2.5 py-1 rounded-full bg-[#f5e9ec] text-[#9b3b4f] ${className}`} data-testid="program-full-badge"><Hourglass size={12} /> Program full · waitlist open</span>
  ) : (
    <span className={`inline-flex items-center gap-1 text-[11.5px] font-semibold px-2.5 py-1 rounded-full bg-[#e9f3e6] text-[#3c7a2f] ${className}`} data-testid="program-seats-badge"><Users size={12} /> {p.seats_left} spot{p.seats_left === 1 ? '' : 's'} remaining</span>
  );
};

const Done = ({ waitlist, email }) => (
  <div className="text-center" data-testid="program-signup-success">
    <CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" />
    <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-1">{waitlist ? "You're on the waitlist!" : "You're signed up!"}</p>
    <p className="text-[14px] text-[#241019]/65">We've emailed a confirmation to <strong>{email}</strong>. {waitlist ? "We'll reach out as soon as a spot opens up." : 'Our team will reach out within 3 business days.'}</p>
  </div>
);

export const ProgramSignup = ({ program: p }) => {
  const [form, setForm] = useState({ name: '', email: '', phone: '', message: '' });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const [error, setError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try { const { data } = await api.post(`/programs/${encodeURIComponent(p.slug)}/signup`, form); setDone({ waitlist: !!data.waitlist }); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  return (
    <section className="py-16 lg:py-20" id="join" data-testid="program-signup">
      <div className="max-w-3xl mx-auto px-5 lg:px-8">
        <div className="bg-white rounded-[24px] p-8 lg:p-10 border border-[#3B0A2E]/8">
          {done ? <Done waitlist={done.waitlist} email={form.email} /> : (
            <form onSubmit={submit}>
              <h2 className="font-serif text-[28px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><UserPlus size={24} className="text-[#B4247E]" /> {p.full ? 'Join the waitlist' : 'Join this program'}</h2>
              <p className="text-[14px] text-[#241019]/65 mb-3">{p.full ? `${p.title} is currently full. Join the waitlist and we'll contact you when a spot opens.` : `Interested in ${p.title}? Leave your details and our team will be in touch.`}</p>
              <SeatsBadge p={p} className="mb-5" />
              <div className="grid sm:grid-cols-2 gap-4 mt-2">
                <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Full Name</label><input required value={form.name} onChange={set('name')} className={inp} data-testid="signup-name-input" /></div>
                <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Email</label><input required type="email" value={form.email} onChange={set('email')} className={inp} data-testid="signup-email-input" /></div>
              </div>
              <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">Phone (optional)</label><input type="tel" value={form.phone} onChange={set('phone')} className={inp} data-testid="signup-phone-input" /></div>
              <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">Message (optional)</label><textarea rows={3} value={form.message} onChange={set('message')} className={`${inp} resize-y`} data-testid="signup-message-input" /></div>
              {error && <p className="text-[13px] text-red-600 mt-3" data-testid="signup-error">{error}</p>}
              <button type="submit" disabled={busy} data-testid="signup-submit-btn" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px] mt-5 flex items-center gap-2 disabled:opacity-60">
                {busy && <Loader2 size={16} className="animate-spin" />} {p.full ? 'Join Waitlist' : 'Sign Me Up'}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
};
