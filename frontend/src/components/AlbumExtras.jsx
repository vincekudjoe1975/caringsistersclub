import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Share2, Link2, Check, Facebook, MessageCircle, ArrowRight } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';

export function ShareButtons({ title, text }) {
  const [copied, setCopied] = useState(false);
  const url = window.location.href;
  const enc = encodeURIComponent;
  const copy = async () => { try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (e) { console.error('Copy failed', e); } };
  const native = async () => { try { await navigator.share({ title, text, url }); } catch (e) { /* user cancelled */ } };
  const btn = 'w-10 h-10 rounded-full flex items-center justify-center border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] transition-colors';
  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="album-share">
      <span className="text-[12px] uppercase tracking-[0.2em] text-[#241019]/50 mr-1">Share this story</span>
      {typeof navigator !== 'undefined' && navigator.share && <button data-testid="share-native" onClick={native} className={btn} aria-label="Share"><Share2 size={16} /></button>}
      <a data-testid="share-facebook" href={`https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`} target="_blank" rel="noopener noreferrer" className={btn} aria-label="Facebook"><Facebook size={16} /></a>
      <a data-testid="share-whatsapp" href={`https://wa.me/?text=${enc(`${title} ${url}`)}`} target="_blank" rel="noopener noreferrer" className={btn} aria-label="WhatsApp"><MessageCircle size={16} /></a>
      <a data-testid="share-x" href={`https://twitter.com/intent/tweet?text=${enc(title)}&url=${enc(url)}`} target="_blank" rel="noopener noreferrer" className={`${btn} font-bold text-[14px]`} aria-label="X">𝕏</a>
      <button data-testid="share-copy" onClick={copy} className={`${btn} ${copied ? 'border-green-600 text-green-700' : ''}`} aria-label="Copy link">{copied ? <Check size={16} /> : <Link2 size={16} />}</button>
    </div>
  );
}

export function LatestAlbum() {
  const [a, setA] = useState(null);
  useEffect(() => { api.get('/gallery/albums').then(({ data }) => setA(data.items[0] || null)).catch(() => {}); }, []);
  if (!a) return null;
  return (
    <section className="py-20 lg:py-24" data-testid="home-latest-album">
      <div className="max-w-7xl mx-auto px-5 lg:px-8">
        <Link to={`/gallery/album/${a.slug}`} data-testid="home-latest-album-link" className="group grid lg:grid-cols-[1.25fr_1fr] rounded-[28px] overflow-hidden bg-white border border-[#3B0A2E]/8 transition-shadow duration-500 hover:shadow-[0_40px_80px_-40px_rgba(59,10,46,0.5)]">
          <div className="h-72 lg:h-[420px] overflow-hidden">{a.cover_url && <img loading="lazy" decoding="async" src={mediaSrc(a.cover_url)} alt={a.title} className="w-full h-full object-cover transition-transform duration-[1200ms] group-hover:scale-[1.05]" />}</div>
          <div className="p-8 lg:p-12 flex flex-col justify-center">
            <p className="eyebrow text-[#B4247E] mb-3">From the gallery{a.date ? ` · ${new Date(`${a.date}T12:00:00`).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}` : ''}</p>
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold leading-tight">{a.title}</h2>
            {a.story && <p className="text-[15px] leading-relaxed text-[#241019]/70 mt-4 line-clamp-4">{a.story}</p>}
            <span className="inline-flex items-center gap-2 mt-6 text-[#B4247E] font-semibold text-[14px]">See all {a.count} photos <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" /></span>
          </div>
        </Link>
      </div>
    </section>
  );
}
