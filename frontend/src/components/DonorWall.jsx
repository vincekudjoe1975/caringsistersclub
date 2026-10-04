import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import Reveal from './Reveal';
import { Heart, TrendingUp, Users } from 'lucide-react';

function timeAgo(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function DonorWall() {
  const [data, setData] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/donations/public');
        setData(res.data);
      } catch (e) {
        console.error('DonorWall: failed to load public donations', e);
      }
    })();
  }, []);

  if (!data) return null;

  const pct = data.goal > 0 ? Math.min(100, Math.round((data.total_raised / data.goal) * 100)) : 0;
  const fmt = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  return (
    <section className="py-20 lg:py-24" style={{ background: '#F7EFE9' }}>
      <div className="max-w-6xl mx-auto px-5 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <p className="eyebrow text-[#B4247E] mb-4">Our Community of Givers</p>
          <h2 className="font-serif text-[32px] lg:text-[42px] text-[#3B0A2E] font-semibold">Together we're making it happen</h2>
        </div>

        <div className="grid lg:grid-cols-[1.3fr_1fr] gap-10 items-start">
          {/* Thermometer */}
          <Reveal>
            <div className="bg-white rounded-2xl p-8 border border-[#3B0A2E]/8">
              <div className="flex items-end justify-between mb-5">
                <div>
                  <p className="font-serif text-[40px] lg:text-[48px] text-[#3B0A2E] font-bold leading-none">{fmt(data.total_raised)}</p>
                  <p className="text-[#241019]/60 text-[14px] mt-2">raised of {fmt(data.goal)} goal</p>
                </div>
                <span className="text-[#B4247E] font-serif text-[30px] font-bold">{pct}%</span>
              </div>
              <div className="h-5 rounded-full overflow-hidden" style={{ background: '#eadfe6' }}>
                <div className="h-full rounded-full transition-all duration-1000 flex items-center justify-end pr-2"
                  style={{ width: `${Math.max(pct, 3)}%`, background: 'linear-gradient(90deg,#B4247E,#D14FA0)' }}>
                  <Heart size={12} className="text-white fill-white" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-7">
                <div className="flex items-center gap-3">
                  <span className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: '#faf2f7' }}><Users size={18} className="text-[#B4247E]" /></span>
                  <div>
                    <p className="font-serif text-[20px] text-[#3B0A2E] font-bold leading-none">{data.donor_count}</p>
                    <p className="text-[#241019]/55 text-[12px] mt-1">generous gifts</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: '#faf2f7' }}><TrendingUp size={18} className="text-[#B4247E]" /></span>
                  <div>
                    <p className="font-serif text-[20px] text-[#3B0A2E] font-bold leading-none">{pct}%</p>
                    <p className="text-[#241019]/55 text-[12px] mt-1">of our goal</p>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>

          {/* Recent supporters */}
          <Reveal delay={120}>
            <div className="bg-white rounded-2xl p-7 border border-[#3B0A2E]/8">
              <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-5">Recent supporters</h3>
              {data.recent.length === 0 ? (
                <p className="text-[#241019]/50 text-[14px]">Be the first to give and start the wall!</p>
              ) : (
                <ul className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                  {data.recent.map((r, i) => (
                    <li key={`${r.name}-${r.date}-${i}`} className="flex items-center justify-between gap-3 pb-3 border-b border-[#3B0A2E]/8 last:border-0">
                      <div className="flex items-center gap-3">
                        <span className="w-9 h-9 rounded-full flex items-center justify-center text-white text-[13px] font-serif font-bold shrink-0" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
                          {r.name === 'Anonymous' ? '?' : r.name.charAt(0)}
                        </span>
                        <div>
                          <p className="text-[14px] text-[#3B0A2E] font-semibold leading-tight">{r.name}</p>
                          <p className="text-[11.5px] text-[#241019]/50">{timeAgo(r.date)}{r.frequency === 'monthly' ? ' · monthly' : ''}</p>
                        </div>
                      </div>
                      <span className="text-[#B4247E] font-semibold text-[14px]">${Number(r.amount).toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
