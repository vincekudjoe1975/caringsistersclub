import { useEffect, useState } from 'react';
import { api } from './api';
import { financials as mockFin, stats as mockStats } from '../mock/mock';

const FALLBACK = { breakdown: mockFin.breakdown, stats: mockStats, financials: [], reports: [], headline_text: '', updated_at: null };
let cache = null;

export function useTransparency() {
  const [data, setData] = useState(cache || FALLBACK);
  useEffect(() => {
    if (cache) return;
    api.get('/transparency').then(({ data: d }) => { cache = d; setData(d); })
      .catch((e) => console.error('Transparency: load failed', e));
  }, []);
  return data;
}

export const resetTransparencyCache = () => { cache = null; };
