import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, Share2, Link2, Mail, Check } from 'lucide-react';
import { api } from '../lib/api';

export const useCampaign = () => {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.get('/donations/public').then(({ data }) => alive && setD(data)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return d;
};

export const ShareCampaign = ({ title, dark = false }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const url = `${window.location.origin}/donate`;
  const text = `Help The Caring Sisters Club reach our goal: ${title || 'our campaign'}`;
  const e = encodeURIComponent;
  const share = async () => {
    if (navigator.share) { try { await navigator.share({ title: text, url }); return; } catch { /* fall through */ } }
    setOpen((o) => !o);
  };
  const copy = async () => { await navigator.clipboard?.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  const links = [['Facebook', `https://www.facebook.com/sharer/sharer.php?u=${e(url)}`], ['X', `https://twitter.com/intent/tweet?text=${e(text)}&url=${e(url)}`], ['WhatsApp', `https://wa.me/?text=${e(`${text} ${url}`)}`]];
  const pill = `min-h-[40px] rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5 transition-colors ${dark ? 'bg-white/10 text-[#F7EFE9] hover:bg-white/20 border border-white/20' : 'bg-white text-[#3B0A2E] hover:bg-[#faf2f7] border border-[#3B0A2E]/15'}`;
  return (
    <div className="relative" data-testid="share-campaign">
      <button type="button" data-testid="share-campaign-btn" onClick={share} className={pill}><Share2 size={14} /> Share this campaign</button>
      {open && (
        <div data-testid="share-campaign-menu" className="mt-2 flex flex-wrap gap-2">
          <button type="button" data-testid="share-copy-link" onClick={copy} className={pill}>{copied ? <Check size={14} /> : <Link2 size={14} />} {copied ? 'Copied' : 'Copy link'}</button>
          {links.map(([l, href]) => <a key={l} data-testid={`share-${l.toLowerCase()}`} href={href} target="_blank" rel="noopener noreferrer" className={pill}>{l}</a>)}
          <a data-testid="share-email" href={`mailto:?subject=${e(text)}&body=${e(`${text}\n\n${url}`)}`} className={pill}><Mail size={14} /> Email</a>
        </div>
      )}
    </div>
  );
};

export const HomeThermometer = () => {
  const d = useCampaign();
  if (!d || !d.goal) return null;
  const pct = Math.min(100, Math.round((d.total_raised / d.goal) * 100));
  const fmt = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  return (
    <section data-testid="home-thermometer" className="py-14 lg:py-16" style={{ background: '#F7EFE9' }}>
      <div className="max-w-5xl mx-auto px-5 lg:px-8">
        <div className="bg-white rounded-3xl p-6 sm:p-9 border border-[#3B0A2E]/8 grid md:grid-cols-[1fr_auto] gap-6 md:gap-10 items-center">
          <div className="min-w-0">
            <p className="eyebrow text-[#B4247E] mb-2">{d.campaign_subtitle || 'Live campaign'}</p>
            <h2 className="font-serif text-[24px] sm:text-[30px] text-[#3B0A2E] font-semibold leading-tight">{d.campaign_title || 'Help us reach our goal'}</h2>
            <div className="flex items-end justify-between mt-5 mb-2.5">
              <p data-testid="home-thermo-raised" className="font-serif text-[30px] sm:text-[36px] text-[#3B0A2E] font-bold leading-none">{fmt(d.total_raised)}<span className="text-[14px] font-sans font-normal text-[#241019]/60"> of {fmt(d.goal)}</span></p>
              <span data-testid="home-thermo-pct" className="font-serif text-[24px] text-[#B4247E] font-bold">{pct}%</span>
            </div>
            <div className="h-4 rounded-full overflow-hidden bg-[#eadfe6]" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
              <div className="h-full rounded-full flex items-center justify-end pr-1.5 transition-[width] duration-1000" style={{ width: `${Math.max(pct, 3)}%`, background: 'linear-gradient(90deg,#B4247E,#D14FA0)' }}><Heart size={10} className="text-white fill-white" /></div>
            </div>
            <p className="text-[13px] text-[#241019]/60 mt-2.5">{d.donor_count} generous gift{d.donor_count === 1 ? '' : 's'} so far</p>
          </div>
          <div className="flex flex-col items-start md:items-end gap-3">
            <Link to="/donate" data-testid="home-thermo-donate" className="btn-magenta rounded-full px-7 py-3 font-semibold">Give now</Link>
            <ShareCampaign title={d.campaign_title} />
          </div>
        </div>
      </div>
    </section>
  );
};
