import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Star, CheckCircle2, AlertCircle, ThumbsUp, ThumbsDown } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from './Events';

const Shell = ({ children }) => (
  <section className="min-h-[70vh] flex items-center justify-center px-5 py-32" style={{ background: '#F7EFE9' }}>
    <div className="bg-white rounded-[24px] max-w-lg w-full p-9 text-center border border-[#3B0A2E]/8" data-testid="feedback-page">{children}</div>
  </section>
);

function Stars({ value, onChange }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex justify-center gap-1.5 mb-6" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" onClick={() => onChange(n)} onMouseEnter={() => setHover(n)} data-testid={`feedback-star-${n}`} aria-label={`${n} star${n > 1 ? 's' : ''}`} className="transition-transform hover:scale-110">
          <Star size={36} className="text-[#CBA24B]" fill={(hover || value) >= n ? '#CBA24B' : 'none'} />
        </button>
      ))}
    </div>
  );
}

export default function Feedback() {
  const q = new URLSearchParams(window.location.search);
  const token = q.get('token') || '';
  const pre = Number(q.get('rating'));
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [rating, setRating] = useState(pre >= 1 && pre <= 5 ? pre : 0);
  const [recommend, setRecommend] = useState(null);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.get(`/feedback?token=${encodeURIComponent(token)}`).then(({ data }) => {
      setInfo(data);
      if (data.submitted) { setRating(data.rating); setRecommend(data.recommend); setComment(data.comment || ''); }
    }).catch((e) => setError(errMsg(e)));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await api.post('/feedback', { token, rating, recommend, comment }); setDone(true); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  if (error) return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Something's not right</p><p className="text-[14px] text-[#241019]/65" data-testid="feedback-error">{error}</p></Shell>;
  if (!info) return <Shell><Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} /></Shell>;
  if (done) return <Shell><CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2" data-testid="feedback-success">Thank you, {info.name}!</p><p className="text-[14px] text-[#241019]/65 mb-6">Your feedback helps us make every session better.</p><Link to="/sessions" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">See Upcoming Sessions</Link></Shell>;
  const pill = (v, label, Icon) => (
    <button type="button" onClick={() => setRecommend(v)} data-testid={`feedback-recommend-${v ? 'yes' : 'no'}`} className={`flex-1 py-2.5 rounded-full text-[13.5px] font-semibold flex items-center justify-center gap-1.5 border transition-colors ${recommend === v ? 'bg-[#3B0A2E] text-white border-[#3B0A2E]' : 'text-[#3B0A2E] border-[#3B0A2E]/15'}`}><Icon size={15} /> {label}</button>
  );
  return (
    <Shell>
      <form onSubmit={submit}>
        <p className="text-[12px] uppercase tracking-[0.18em] font-semibold text-[#B4247E] mb-2">Session feedback</p>
        <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-1">How was {info.program}?</h1>
        <p className="text-[14px] text-[#241019]/60 mb-6">{info.submitted ? 'You can update your answers below.' : `Hi ${info.name}, thanks for joining us!`}</p>
        <Stars value={rating} onChange={setRating} />
        <p className="text-[13.5px] font-semibold text-[#3B0A2E] mb-2">Would you recommend it to a friend?</p>
        <div className="flex gap-2 mb-5">{pill(true, 'Yes', ThumbsUp)}{pill(false, 'No', ThumbsDown)}</div>
        <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1500} placeholder="Anything you'd like to share? (optional)" data-testid="feedback-comment-input" className="w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-3 text-[14px] mb-5 focus:outline-none focus:border-[#B4247E]" />
        <button type="submit" disabled={!rating || busy} data-testid="feedback-submit-btn" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px] disabled:opacity-50">{busy ? 'Sending…' : 'Send Feedback'}</button>
      </form>
    </Shell>
  );
}
