import React, { useEffect, useState, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../lib/api';
import PageHero from '../components/PageHero';
import { CheckCircle2, Loader2, XCircle, Heart } from 'lucide-react';

const MAX_ATTEMPTS = 8;
const INTERVAL_MS = 2000;

export default function PaymentSuccess() {
  const location = useLocation();
  const [state, setState] = useState('checking'); // checking | paid | timeout | error
  const [info, setInfo] = useState(null);
  const attempts = useRef(0);

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
