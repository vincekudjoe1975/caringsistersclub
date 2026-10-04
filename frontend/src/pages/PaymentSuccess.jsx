import React, { useEffect, useState, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../lib/api';
import PageHero from '../components/PageHero';
import { CheckCircle2, Loader2, XCircle, Heart, Share2, Facebook, Twitter, Linkedin } from 'lucide-react';

const MAX_ATTEMPTS = 8;
const INTERVAL_MS = 2000;

export default function PaymentSuccess() {
  const location = useLocation();
  const [state, setState] = useState('checking'); // checking | paid | timeout | error
  const [info, setInfo] = useState(null);
  const [copied, setCopied] = useState(false);
  const attempts = useRef(0);

  const siteUrl = window.location.origin;
  const shareText = 'I just donated to The Caring Sisters Club, empowering women of the Diaspora. Join me!';
  const shareLinks = {
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(siteUrl)}`,
    twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(siteUrl)}`,
    linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(siteUrl)}`,
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: 'The Caring Sisters Club', text: shareText, url: siteUrl });
        return;
      } catch (e) {
        /* user cancelled or unsupported; fall through to copy */
      }
    }
    try {
      await navigator.clipboard.writeText(`${shareText} ${siteUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) {
      console.error('Share: clipboard failed', e);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const sessionId = params.get('session_id');
    if (!sessionId) { setState('error'); return; }
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      attempts.current += 1;
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        if (data.payment_status === 'paid') {
          setInfo(data);
          setState('paid');
          return;
        }
        if (data.status === 'expired') { setState('error'); return; }
      } catch (e) {
        if (attempts.current >= MAX_ATTEMPTS) { setState('error'); return; }
      }
      if (attempts.current >= MAX_ATTEMPTS) { setState('timeout'); return; }
      setTimeout(poll, INTERVAL_MS);
    };
    poll();
    return () => { cancelled = true; };
  }, [location.search]);

  return (
    <div>
      <PageHero kicker="Donation" title={state === 'paid' ? 'Thank you, Sister!' : 'Processing your gift'} align="center" />
      <section className="py-24">
        <div className="max-w-lg mx-auto px-5 text-center">
          {state === 'checking' && (
            <>
              <Loader2 size={56} className="text-[#B4247E] mx-auto mb-6 animate-spin" />
              <p className="text-[#241019]/70">Confirming your payment with Stripe…</p>
            </>
          )}
          {state === 'paid' && (
            <>
              <CheckCircle2 size={64} className="text-[#B4247E] mx-auto mb-6" />
              <h2 className="font-serif text-[30px] text-[#3B0A2E] font-semibold mb-4">Your gift makes a difference</h2>
              <p className="text-[#241019]/70 mb-3">
                Your {info?.frequency === 'monthly' ? 'monthly' : 'one-time'} contribution of <strong>${info?.amount}</strong> was received. Thank you!
              </p>
              <p className="text-[#241019]/50 text-[13px] mb-8">A receipt has been emailed by Stripe. Your gift is tax-deductible to the extent allowed by law.</p>

              {/* Shareable "I gave" badge */}
              <div className="rounded-2xl p-6 mb-8 text-left" style={{ background: 'linear-gradient(135deg,#3B0A2E,#4d1240)' }}>
                <div className="flex items-center gap-4">
                  <span className="w-14 h-14 rounded-full flex items-center justify-center shrink-0" style={{ background: 'rgba(203,162,75,0.2)' }}>
                    <Heart size={26} className="text-[#CBA24B] fill-[#CBA24B]" />
                  </span>
                  <div>
                    <p className="font-serif text-[#F7EFE9] text-[18px] font-semibold leading-tight">I gave to the Caring Sisters Club</p>
                    <p className="text-[#F7EFE9]/70 text-[13px] mt-1">Empowering women of the Diaspora. Join me &mdash; every gift counts.</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2.5 mt-5">
                  <button onClick={handleShare} className="btn-gold rounded-full px-5 py-2.5 font-semibold text-[13.5px] flex items-center gap-2">
                    <Share2 size={15} /> {copied ? 'Copied!' : 'Share'}
                  </button>
                  <a href={shareLinks.facebook} target="_blank" rel="noreferrer" className="btn-outline-cream rounded-full w-10 h-10 flex items-center justify-center"><Facebook size={16} /></a>
                  <a href={shareLinks.twitter} target="_blank" rel="noreferrer" className="btn-outline-cream rounded-full w-10 h-10 flex items-center justify-center"><Twitter size={16} /></a>
                  <a href={shareLinks.linkedin} target="_blank" rel="noreferrer" className="btn-outline-cream rounded-full w-10 h-10 flex items-center justify-center"><Linkedin size={16} /></a>
                </div>
              </div>

              <div className="flex justify-center gap-4">
                <Link to="/" className="btn-outline-cream rounded-full px-7 py-3 font-semibold" style={{ borderColor: '#3B0A2E40', color: '#3B0A2E' }}>Back Home</Link>
                <Link to="/donate" className="btn-magenta rounded-full px-7 py-3 font-semibold flex items-center gap-2"><Heart size={16} className="fill-white" /> Give Again</Link>
              </div>
            </>
          )}
          {state === 'timeout' && (
            <>
              <Loader2 size={56} className="text-[#CBA24B] mx-auto mb-6" />
              <h2 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3">Still processing</h2>
              <p className="text-[#241019]/70 mb-8">Your payment is taking a little longer to confirm. If funds were charged, you'll receive a receipt shortly.</p>
              <Link to="/" className="btn-magenta rounded-full px-7 py-3 font-semibold">Back Home</Link>
            </>
          )}
          {state === 'error' && (
            <>
              <XCircle size={56} className="text-red-500 mx-auto mb-6" />
              <h2 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3">We couldn't confirm this payment</h2>
              <p className="text-[#241019]/70 mb-8">If you believe this is an error, please contact us and we'll help right away.</p>
              <div className="flex justify-center gap-4">
                <Link to="/donate" className="btn-magenta rounded-full px-7 py-3 font-semibold">Try Again</Link>
                <Link to="/contact" className="btn-outline-cream rounded-full px-7 py-3 font-semibold" style={{ borderColor: '#3B0A2E40', color: '#3B0A2E' }}>Contact Us</Link>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
