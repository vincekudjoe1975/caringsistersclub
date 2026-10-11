import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ShieldAlert, Loader2 } from 'lucide-react';
import { api } from '../lib/api';

const day = (s) => new Date(`${s}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short' });

export function SpamCard() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/security/spam').then(({ data }) => setD(data)).catch(() => setD({ days: [], today: 0, week_total: 0 })); }, []);
  return (
    <div data-testid="spam-card" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <p className="eyebrow text-[#B4247E] mb-1 flex items-center gap-1.5"><ShieldAlert size={14} /> Site security</p>
          <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold">Blocked spam, last 7 days</h3>
        </div>
        {d && (
          <div className="flex gap-6 text-right">
            <div><p className="text-[11px] uppercase tracking-wide text-[#241019]/50">Today</p><p data-testid="spam-today" className="font-serif text-[26px] text-[#3B0A2E] font-semibold">{d.today}</p></div>
            <div><p className="text-[11px] uppercase tracking-wide text-[#241019]/50">7 days</p><p data-testid="spam-week" className="font-serif text-[26px] text-[#3B0A2E] font-semibold">{d.week_total}</p></div>
          </div>
        )}
      </div>
      {!d ? <Loader2 className="animate-spin text-[#B4247E]" /> : (
        <>
          <div className="h-44" data-testid="spam-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d.days.map((x) => ({ ...x, label: day(x.date) }))} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: '#6b5560' }} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#8a7380' }} />
                <Tooltip cursor={{ fill: 'rgba(180,36,126,0.06)' }} formatter={(v) => [v, 'Blocked']} labelFormatter={(l, p) => (p?.[0]?.payload?.date ? new Date(`${p[0].payload.date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }) : l)} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {d.days.map((x, i) => <Cell key={x.date} fill={i === d.days.length - 1 ? '#B4247E' : '#3B0A2E'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p data-testid="spam-top-form" className="text-[13px] text-[#241019]/65 mt-3">
            {d.top_form ? <>Most targeted: <strong className="text-[#3B0A2E]">{d.top_form.label}</strong> ({d.top_form.count} blocked this week)</> : 'No spam blocked this week. All quiet.'}
          </p>
          <p className="text-[11.5px] text-[#241019]/45 mt-1">Blocked requests are stopped automatically. Staff get a daily summary email when anything is blocked.</p>
        </>
      )}
    </div>
  );
}

export default function AdminOverview() {
  return (
    <div data-testid="admin-overview" className="max-w-3xl">
      <SpamCard />
    </div>
  );
}
