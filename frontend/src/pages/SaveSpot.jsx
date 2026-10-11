import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Loader2, CheckCircle2, CalendarDays } from 'lucide-react';

export default function SaveSpot() {
  const [sp] = useSearchParams();
  const token = sp.get('token') || '';
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get('/sessions/save-spot', { params: { token } }).then(({ data }) => { setD(data); setDone(data.used); }).catch((e) => setErr(e?.response?.data?.detail || 'This link is not valid.')); }, [token]);
  const save = async () => {
    setBusy(true); setErr('');
    try { await api.post('/sessions/save-spot', { token }); setDone(true); }
    catch (e) { setErr(e?.response?.data?.detail || 'Could not save your spot.'); }
    finally { setBusy(false); }
  };
  return (
    <section className="csc-hero-gradient min-h-[80vh] flex items-center justify-center px-5 py-32">
      <div data-testid="save-spot-page" className="bg-white rounded-3xl p-9 max-w-md w-full text-center animate-[zoomIn_.4s_ease]" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
        {!d && !err ? <Loader2 className="animate-spin mx-auto text-[#B4247E]" /> : !d ? <p data-testid="save-spot-error" className="text-[#241019]/70">{err} <Link to="/sessions" className="text-[#B4247E] font-semibold">See upcoming sessions</Link></p> : done ? (
          <div data-testid="save-spot-done">
            <CheckCircle2 size={56} className="mx-auto text-green-600 mb-3" />
            <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold">Your spot is saved{d.name ? `, ${d.name}` : ''}!</h1>
            <p className="text-[14px] text-[#241019]/70 mt-2">{d.program}<br />{d.label}</p>
            <p className="text-[13px] text-[#241019]/55 mt-3">A confirmation is on its way to your inbox.</p>
          </div>
        ) : (
          <>
            <p className="eyebrow text-[#CBA24B] mb-2">We'd love to see you</p>
            <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold leading-tight">{d.program}</h1>
            <p data-testid="save-spot-label" className="text-[14px] text-[#241019]/70 mt-2 flex items-center justify-center gap-1.5"><CalendarDays size={15} /> {d.label}</p>
            {d.full || d.past ? <p data-testid="save-spot-unavailable" className="text-[14px] text-[#241019]/70 mt-6">{d.past ? 'This session has already happened.' : 'This session just filled up.'} <Link to={`/initiatives/${d.slug}`} className="text-[#B4247E] font-semibold">Choose another date</Link></p> : (
              <button data-testid="save-spot-btn" onClick={save} disabled={busy} className="btn-magenta rounded-full w-full py-3.5 font-semibold mt-7 flex items-center justify-center gap-2 disabled:opacity-60">{busy && <Loader2 size={16} className="animate-spin" />} Save my spot</button>
            )}
            {err && <p data-testid="save-spot-msg" className="text-red-600 text-[13px] mt-3">{err}</p>}
          </>
        )}
      </div>
    </section>
  );
}
