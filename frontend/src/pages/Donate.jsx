import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { donationTiers, org } from '../mock/mock';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import DonorWall from '../components/DonorWall';
import { Heart, ShieldCheck, Repeat, CreditCard, CheckCircle2, Loader2 } from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import { api } from '../lib/api';

export default function Donate() {
  const [amount, setAmount] = useState(50);
  const [custom, setCustom] = useState('');
  const [freq, setFreq] = useState('one-time');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const a = new URLSearchParams(window.location.search).get('appeal');
    if (a && /^[0-9a-f-]{36}$/i.test(a)) sessionStorage.setItem('csc_appeal', a);
  }, []);

  const finalAmount = custom ? Number(custom) : amount;

  const submit = async (e) => {
    e.preventDefault();
    if (!finalAmount || finalAmount <= 0) {
      toast({ title: 'Please choose an amount', variant: 'destructive' });
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post('/payments/checkout', {
        amount: finalAmount,
        frequency: freq,
        donor_name: name,
        donor_email: email,
        anonymous: anonymous,
        origin_url: window.location.origin,
        appeal_id: sessionStorage.getItem('csc_appeal') || undefined,
      });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        throw new Error('No checkout URL');
      }
    } catch (err) {
      setLoading(false);
      toast({ title: 'Could not start checkout', description: err?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    }
  };

  return (
    <div>
      <PageHero
        kicker="Support the Sisterhood"
        title="Your gift empowers women of the Diaspora"
        subtitle="Every contribution fuels professional programs, housing support, and community care. 82¢ of every dollar goes directly to our sisters."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-5xl mx-auto px-5 lg:px-8 grid lg:grid-cols-[1fr_360px] gap-10 items-start">
          <form onSubmit={submit} className="bg-white rounded-2xl p-8 lg:p-10 border border-[#3B0A2E]/8">
            {/* Frequency */}
            <div className="flex gap-2 p-1.5 rounded-full mb-8" style={{ background: '#F7EFE9' }}>
              {[{ k: 'one-time', l: 'One-Time' }, { k: 'monthly', l: 'Monthly' }].map((f) => (
                <button key={f.k} type="button" onClick={() => setFreq(f.k)}
                  className={`flex-1 py-2.5 rounded-full text-[14px] font-semibold flex items-center justify-center gap-2 transition-all ${freq === f.k ? 'text-white' : 'text-[#3B0A2E]'}`}
                  style={freq === f.k ? { background: '#B4247E' } : {}}>
                  {f.k === 'monthly' && <Repeat size={15} />} {f.l}
                </button>
              ))}
            </div>

            <p className="eyebrow text-[#B4247E] mb-4">Choose an amount</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
              {donationTiers.map((t) => (
                <button key={t.amount} type="button" onClick={() => { setAmount(t.amount); setCustom(''); }}
                  className={`rounded-xl py-4 border-2 transition-all ${amount === t.amount && !custom ? 'border-[#B4247E]' : 'border-[#3B0A2E]/12 hover:border-[#B4247E]/40'}`}
                  style={amount === t.amount && !custom ? { background: '#faf2f7' } : {}}>
                  <p className="font-serif text-[24px] text-[#3B0A2E] font-bold">${t.amount}</p>
                  <p className="text-[11px] text-[#B4247E] font-semibold">{t.label}</p>
                </button>
              ))}
            </div>
            <div className="relative mb-6">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#3B0A2E] font-semibold">$</span>
              <input type="number" min={1} placeholder="Other amount" value={custom} onChange={(e) => setCustom(e.target.value)}
                className="w-full rounded-xl border-2 border-[#3B0A2E]/12 pl-8 pr-4 py-3.5 text-[15px] focus:outline-none focus:border-[#B4247E]" />
            </div>

            {custom && donationTiers.find((t) => t.amount === Number(custom)) === undefined && (
              <p className="text-[13px] text-[#241019]/60 mb-4">Thank you for your generous ${custom} gift.</p>
            )}
            {!custom && (
              <p className="text-[13.5px] text-[#241019]/70 mb-6 flex items-start gap-2">
                <Heart size={16} className="text-[#B4247E] shrink-0 mt-0.5" /> {donationTiers.find((t) => t.amount === amount)?.desc}
              </p>
            )}

            <div className="grid sm:grid-cols-2 gap-4 mb-5">
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Name <span className="text-[#241019]/40 font-normal">(optional)</span></label>
                <input value={name} onChange={(e) => setName(e.target.value)}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Email <span className="text-[#241019]/40 font-normal">(optional)</span></label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
            </div>

            <label className="flex items-center gap-2.5 mb-5 cursor-pointer select-none">
              <input type="checkbox" checked={anonymous} onChange={(e) => setAnonymous(e.target.checked)}
                className="w-4 h-4 accent-[#B4247E]" />
              <span className="text-[13.5px] text-[#3B0A2E]">Appear anonymously on the donor wall</span>
            </label>

            <div className="rounded-xl p-4 mb-6 flex items-center gap-3" style={{ background: '#F7EFE9' }}>
              <CreditCard size={20} className="text-[#B4247E]" />
              <p className="text-[12.5px] text-[#3B0A2E]/70">Secure checkout by Stripe. Test mode: use card <strong>4242 4242 4242 4242</strong>, any future expiry & CVC.</p>
            </div>

            {freq === 'monthly' && (
              <p className="text-[12.5px] text-[#241019]/60 mb-4" data-testid="donate-manage-note">
                Update your card or cancel anytime from <Link to="/manage-gift" className="text-[#B4247E] font-semibold hover:underline">Manage My Monthly Gift</Link>.
              </p>
            )}
            <button type="submit" disabled={loading} className="btn-magenta rounded-full w-full py-4 font-semibold text-[16px] flex items-center justify-center gap-2 disabled:opacity-60">
              {loading ? <><Loader2 className="animate-spin" size={18} /> Redirecting…</> : <><Heart size={18} className="fill-white" /> Give ${finalAmount || 0} {freq === 'monthly' ? '/ month' : ''}</>}
            </button>
          </form>

          <Reveal delay={120} className="space-y-5">
            <div className="rounded-2xl p-7 text-white" style={{ background: 'linear-gradient(160deg,#3B0A2E,#4d1240)' }}>
              <ShieldCheck className="text-[#CBA24B] mb-4" size={28} />
              <h3 className="font-serif text-[20px] font-semibold mb-2">Tax-deductible & secure</h3>
              <p className="text-[#F7EFE9]/75 text-[14px] leading-relaxed">
                {org.name} is a {org.status}. Gifts are tax-deductible to the extent allowed by law.
              </p>
            </div>
            <div className="rounded-2xl p-7 bg-white border border-[#3B0A2E]/8">
              <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-4">Your impact</h3>
              <ul className="space-y-3 text-[14px] text-[#241019]/75">
                {donationTiers.map((t) => (
                  <li key={t.amount} className="flex gap-2.5"><CheckCircle2 size={17} className="text-[#B4247E] shrink-0 mt-0.5" /><span><strong>${t.amount}</strong> — {t.desc}</span></li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </section>
      <DonorWall />
    </div>
  );
}
