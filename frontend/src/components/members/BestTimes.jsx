import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const hr = (h) => `${h % 12 || 12}${h < 12 ? 'am' : 'pm'}`;
export const bestLabel = (b) => `${DAYS[b.day]} around ${hr(b.hour)}`;

export const useBestTimes = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/members/push/best-times').then(({ data }) => setD(data)).catch(() => {}); }, []);
  return d;
};

export const BestTimes = ({ d }) => {
  if (!d) return null;
  const max = Math.max(1, ...d.grid.flat());
  return (
    <div data-testid="best-times" className="mt-6 pt-5 border-t border-[#3B0A2E]/10">
      <p className="font-semibold text-[#3B0A2E]">Best send times <span className="font-normal text-[13px] text-[#241019]/55">· taps in the last 90 days, Eastern</span></p>
      {!d.total ? <p data-testid="best-times-empty" className="text-[13px] text-[#241019]/55 mt-1">Not enough taps yet. This fills in as sisters tap alerts.</p> : (
        <>
          <p data-testid="best-times-top" className="text-[13px] text-[#241019]/70 mt-1">Most taps: {d.best.map(bestLabel).join(' · ')}</p>
          <div className="overflow-x-auto mt-3">
            <div className="grid gap-[3px] min-w-[560px]" style={{ gridTemplateColumns: '36px repeat(24, minmax(0, 1fr))' }}>
              <span />{Array.from({ length: 24 }, (_, h) => <span key={h} className="text-[10.5px] text-[#241019]/45 text-center">{h % 3 === 0 ? hr(h) : ''}</span>)}
              {d.grid.map((row, di) => (
                <React.Fragment key={di}>
                  <span className="text-[12px] text-[#241019]/60 font-semibold">{DAYS[di]}</span>
                  {row.map((n, h) => <span key={h} data-testid={`best-cell-${di}-${h}`} title={`${DAYS[di]} ${hr(h)}: ${n} tap${n === 1 ? '' : 's'}`} className="h-5 rounded-[3px]" style={{ background: n ? `rgba(180,36,126,${0.15 + 0.85 * (n / max)})` : '#f3ebe6' }} />)}
                </React.Fragment>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
