import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, CalendarX, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from './Events';

const Shell = ({ children }) => (
  <section className="min-h-[70vh] flex items-center justify-center px-5 py-32" style={{ background: '#F7EFE9' }}>
    <div className="bg-white rounded-[24px] max-w-lg w-full p-9 text-center border border-[#3B0A2E]/8" data-testid="release-page">{children}</div>
  </section>
);

export default function SeatRelease() {
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get(`/seat-release?token=${encodeURIComponent(token)}`).then(({ data }) => setInfo(data)).catch((e) => setError(errMsg(e))); }, [token]);
  const release = async () => {
    setBusy(true);
    try { await api.post('/seat-release', { token }); setInfo({ ...info, released: true }); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(false); }
  };
  if (error) return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Link unavailable</p><p className="text-[14px] text-[#241019]/65" data-testid="release-error">{error}</p></Shell>;
  if (!info) return <Shell><Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} /></Shell>;
  if (info.released) return (
    <Shell>
      <CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" />
      <p className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2" data-testid="release-success">Thank you for letting us know</p>
      <p className="text-[14px] text-[#241019]/65 mb-6">Your seat in <strong>{info.program}</strong> has been released and offered to a sister on the waitlist. We hope to see you at a future session!</p>
      <Link to="/sessions" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">See Upcoming Sessions</Link>
    </Shell>
  );
  const date = info.start_date ? new Date(`${info.start_date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }) : '';
  return (
    <Shell>
      <CalendarX size={44} className="text-[#B4247E] mx-auto mb-3" />
      <p className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2">Can't make it{info.name ? `, ${info.name}` : ''}?</p>
      <p className="text-[14px] text-[#241019]/65 mb-6">This will release your seat in <strong>{info.program}</strong>{date ? ` (${date}${info.schedule ? `, ${info.schedule}` : ''})` : ''} so a sister on the waitlist can take it. This can't be undone.</p>
      <button onClick={release} disabled={busy} data-testid="release-confirm-btn" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] disabled:opacity-60">{busy ? 'Releasing…' : 'Yes, release my seat'}</button>
      <p className="mt-4"><Link to="/" data-testid="release-keep-link" className="text-[13px] font-semibold text-[#3B0A2E]/70 hover:text-[#B4247E]">No, keep my seat</Link></p>
    </Shell>
  );
}
