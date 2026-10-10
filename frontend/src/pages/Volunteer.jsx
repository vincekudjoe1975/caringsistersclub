import React, { useState } from 'react';
import { api } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { CheckCircle2, Users, HandHeart, Loader2 } from 'lucide-react';
import { LogHours, Leaderboard, CertificateRequest } from '../components/VolunteerHours';
import { useToast } from '../hooks/use-toast';

const interests = ['Events & Programs', 'Community Drives', 'Mentorship', 'Fundraising', 'Administration', 'Chapter Leadership'];

export default function Volunteer() {
  const [tab, setTab] = useState('volunteer');
  const [form, setForm] = useState({ name: '', email: '', phone: '', city: '', interest: interests[0], message: '' });
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);
  const { toast } = useToast();

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await api.post('/submissions', { type: tab === 'member' ? 'member' : 'volunteer', ...form });
      setSubmitted(true);
      toast({ title: `${tab === 'volunteer' ? 'Volunteer' : 'Membership'} application received!`, description: `Thank you, ${form.name}. A chapter lead will reach out within 3 business days.` });
    } catch (err) {
      toast({ title: 'Application not sent', description: err?.response?.status === 429 ? 'You\'ve sent a few requests in a row. Please wait a minute and try again.' : (err?.response?.data?.detail || 'Something went wrong. Please check your connection and try again.'), variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <PageHero
        kicker="Volunteer & Join"
        title="Become part of the sisterhood"
        subtitle="Whether you want to volunteer your time or join as a member, there's a place for you in our community."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-3xl mx-auto px-5 lg:px-8">
          <div className="flex gap-2 p-1.5 rounded-full mb-10 max-w-md mx-auto" style={{ background: '#F7EFE9' }}>
            {[{ k: 'volunteer', l: 'Volunteer', icon: HandHeart }, { k: 'member', l: 'Become a Member', icon: Users }].map((t) => {
              const Icon = t.icon;
              return (
                <button key={t.k} onClick={() => { setTab(t.k); setSubmitted(false); }}
                  className={`flex-1 py-2.5 rounded-full text-[14px] font-semibold flex items-center justify-center gap-2 transition-all ${tab === t.k ? 'text-white' : 'text-[#3B0A2E]'}`}
                  style={tab === t.k ? { background: '#B4247E' } : {}}>
                  <Icon size={16} /> {t.l}
                </button>
              );
            })}
          </div>

          {submitted ? (
            <Reveal className="bg-white rounded-2xl p-10 text-center border border-[#3B0A2E]/8">
              <CheckCircle2 size={56} className="text-[#B4247E] mx-auto mb-5" />
              <h2 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3" data-testid="volunteer-success">Welcome, Sister!</h2>
              <p className="text-[#241019]/70 mb-6">Your application has been received. A chapter lead will reach out within 3 business days.</p>
              <button onClick={() => { setSubmitted(false); setForm({ name: '', email: '', phone: '', city: '', interest: interests[0], message: '' }); }} className="btn-magenta rounded-full px-8 py-3 font-semibold">Submit Another</button>
            </Reveal>
          ) : (
            <form onSubmit={submit} className="bg-white rounded-2xl p-8 lg:p-10 border border-[#3B0A2E]/8 space-y-5">
              <div className="grid sm:grid-cols-2 gap-5">
                <Field label="Full Name" required value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
                <Field label="Email" type="email" required value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
                <Field label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
                <Field label="City" value={form.city} onChange={(v) => setForm({ ...form, city: v })} />
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Area of Interest</label>
                <select value={form.interest} onChange={(e) => setForm({ ...form, interest: e.target.value })}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E]">
                  {interests.map((i) => <option key={i}>{i}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Tell us about yourself</label>
                <textarea rows={4} value={form.message} data-testid="volunteer-message-input" onChange={(e) => setForm({ ...form, message: e.target.value })}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E] resize-none"
                  placeholder={tab === 'volunteer' ? 'What draws you to volunteer with us?' : 'Why do you want to join the sisterhood?'} />
              </div>
              <button type="submit" disabled={sending} data-testid="volunteer-submit-btn" className="btn-magenta rounded-full w-full py-3.5 font-semibold text-[15px] flex items-center justify-center gap-2 disabled:opacity-60">
                {sending ? <><Loader2 size={16} className="animate-spin" /> Submitting…</> : tab === 'volunteer' ? 'Submit Volunteer Application' : 'Submit Membership Application'}
              </button>
            </form>
          )}
        </div>
      </section>
      <Leaderboard />
      <CertificateRequest />
      <LogHours />
    </div>
  );
}

function Field({ label, type = 'text', required, value, onChange }) {
  return (
    <div>
      <label className="text-[13px] font-semibold text-[#3B0A2E]">{label}{required && <span className="text-[#B4247E]">*</span>}</label>
      <input type={type} required={required} value={value} onChange={(e) => onChange(e.target.value)} data-testid={`volunteer-${label.toLowerCase().replace(/\s+/g, '-')}-input`}
        className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
    </div>
  );
}
