import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Quote, CheckCircle2, AlertCircle, ImagePlus } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';
import { errMsg } from './Events';

const Shell = ({ children }) => (
  <section className="min-h-[70vh] flex items-center justify-center px-5 py-32" style={{ background: '#F7EFE9' }}>
    <div className="bg-white rounded-[24px] max-w-lg w-full p-9 text-center border border-[#3B0A2E]/8" data-testid="feature-words-page">{children}</div>
  </section>
);

export default function FeatureMyWords() {
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [photo, setPhoto] = useState('');
  const [busy, setBusy] = useState('');
  const [done, setDone] = useState(false);
  useEffect(() => { api.get(`/feature-consent?token=${encodeURIComponent(token)}`).then(({ data }) => { setInfo(data); setDone(data.consented); }).catch((e) => setError(errMsg(e))); }, [token]);
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    setBusy('photo');
    try { const { data } = await api.post('/stories/photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); setPhoto(data.url); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(''); }
  };
  const submit = async () => {
    setBusy('send');
    try { await api.post('/feature-consent', { token, photo_url: photo }); setDone(true); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(''); }
  };
  if (error) return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Something's not right</p><p className="text-[14px] text-[#241019]/65" data-testid="feature-words-error">{error}</p></Shell>;
  if (!info) return <Shell><Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} /></Shell>;
  if (done) return <Shell><CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2" data-testid="feature-words-success">Thank you, {info.name}!</p><p className="text-[14px] text-[#241019]/65 mb-6">Our team will review your words and may feature them on our Home page soon.</p><Link to="/" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">Visit Home</Link></Shell>;
  return (
    <Shell>
      <Quote size={36} className="text-[#B4247E] mx-auto mb-3" />
      <h1 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2">May we feature your words?</h1>
      <p className="text-[13.5px] text-[#241019]/60 mb-5">About {info.program || 'your session'}. We'll show your first name and last initial.</p>
      <blockquote className="rounded-xl px-5 py-4 mb-6 text-left italic text-[14px] text-[#3B0A2E]" style={{ background: '#faf2f7', borderLeft: '4px solid #B4247E' }} data-testid="feature-words-quote">"{info.quote}"</blockquote>
      <div className="flex items-center justify-center gap-4 mb-6">
        {photo && <img src={mediaSrc(photo)} alt="Your upload" className="w-16 h-16 rounded-full object-cover" data-testid="feature-words-photo-preview" />}
        <label className="text-[13px] font-semibold text-[#B4247E] flex items-center gap-1.5 cursor-pointer px-4 py-2 rounded-full" style={{ border: '1px solid rgba(180,36,126,0.3)' }}>
          {busy === 'photo' ? <Loader2 size={14} className="animate-spin" /> : <ImagePlus size={14} />} {photo ? 'Change photo' : 'Add a photo (optional)'}
          <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => upload(e.target.files?.[0])} data-testid="feature-words-photo-input" />
        </label>
      </div>
      <button onClick={submit} disabled={!!busy} data-testid="feature-words-submit-btn" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px] disabled:opacity-60">{busy === 'send' ? 'Sending…' : 'Yes, feature my words'}</button>
      <p className="mt-4"><Link to="/" className="text-[13px] font-semibold text-[#3B0A2E]/60 hover:text-[#B4247E]" data-testid="feature-words-decline">No thanks</Link></p>
    </Shell>
  );
}
