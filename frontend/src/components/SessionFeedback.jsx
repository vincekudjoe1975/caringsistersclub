import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, Star, Quote } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const fmt = (v, s = '') => (v === null || v === undefined ? '—' : `${v}${s}`);

function Session({ r, onFeature }) {
  return (
    <div className="border-t border-[#3B0A2E]/8 py-4" data-testid="feedback-session">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <p className="font-semibold text-[#3B0A2E] text-[14.5px]">{r.title}{r.end && <span className="text-[12px] font-normal text-[#241019]/50"> · ended {new Date(`${r.end}T12:00:00`).toLocaleDateString()}</span>}</p>
        <div className="flex gap-4 text-[12.5px] text-[#241019]/65">
          <span className="flex items-center gap-1 font-bold text-[#CBA24B]" data-testid="feedback-avg"><Star size={13} fill="#CBA24B" /> {fmt(r.avg_rating)}</span>
          <span data-testid="feedback-response-rate">{r.responses}/{r.sent} replied ({fmt(r.response_rate, '%')})</span>
          <span data-testid="feedback-recommend">{fmt(r.recommend_pct, '%')} recommend</span>
        </div>
      </div>
      {r.comments.length > 0 && (
        <div className="grid md:grid-cols-2 gap-2">
          {r.comments.map((c) => (
            <div key={c.id} className="rounded-xl px-4 py-3 text-[13px]" style={{ background: '#fdf9fb' }} data-testid="feedback-comment">
              <p className="text-[#241019]/80 mb-2">"{c.comment}"</p>
              <div className="flex items-center justify-between text-[11.5px]">
                <span className="text-[#B4247E] font-semibold">{c.name} · {c.rating}★</span>
                {c.featured ? <span className="font-semibold text-[#3c7a2f]" data-testid="feedback-featured-label">Featured on program page</span>
                  : <button onClick={() => onFeature(c)} data-testid="feedback-feature-btn" className="font-semibold text-[#3B0A2E] flex items-center gap-1 hover:text-[#B4247E]"><Quote size={11} /> Feature as testimonial</button>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AlertSetting() {
  const { toast } = useToast();
  const [th, setTh] = useState(null);
  useEffect(() => { api.get('/admin/feedback-alert-settings').then(({ data }) => setTh(data.threshold)).catch(() => {}); }, []);
  if (th === null) return null;
  const change = async (e) => {
    const v = Number(e.target.value); setTh(v);
    try { await api.put('/admin/feedback-alert-settings', { threshold: v }); toast({ title: 'Alert setting saved' }); } catch { toast({ title: 'Save failed', variant: 'destructive' }); }
  };
  return (
    <label className="text-[12.5px] font-semibold text-[#3B0A2E] flex items-center gap-2" data-testid="fb-alert-setting">Alert staff at
      <select value={th} onChange={change} data-testid="fb-alert-threshold-select" className="rounded-full px-3 py-1.5 border border-[#3B0A2E]/15 font-normal">
        <option value={2}>2 stars or below</option><option value={3}>3 stars or below</option>
      </select>
      <span className="font-normal text-[#241019]/55">or "Would not recommend"</span>
    </label>
  );
}

export const SessionFeedback = () => {
  const { toast } = useToast();
  const [items, setItems] = useState(null);
  const load = useCallback(() => api.get('/admin/reports/session-feedback').then(({ data }) => setItems(data.items)).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);
  const feature = async (c) => {
    if (!window.confirm(`Show this comment from ${c.name} as a testimonial on the program page?`)) return;
    try { await api.post(`/admin/feedback/${c.id}/feature`); toast({ title: 'Added to program testimonials' }); load(); }
    catch (err) { toast({ title: 'Could not feature', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="session-feedback">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><Star size={18} className="text-[#B4247E]" /> Session feedback</h3>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12.5px] text-[#241019]/55">Sisters with a seat (or marked Attended) get a short feedback email the day after a session ends.</p>
        <AlertSetting />
      </div>
      {!items ? <Loader2 className="animate-spin text-[#B4247E] mt-4" /> : items.length === 0 ? <p className="text-[13px] text-[#241019]/55 mt-4" data-testid="session-feedback-empty">No feedback requests sent yet.</p> : items.map((r) => <Session key={r.program_id} r={r} onFeature={feature} />)}
    </div>
  );
};
