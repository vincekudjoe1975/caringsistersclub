import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Download, Loader2 } from 'lucide-react';
import { fmtDate } from './fmt';

export function Bylaws() {
  const [doc, setDoc] = useState(null);
  const [err, setErr] = useState('');
  const [dl, setDl] = useState(false);
  useEffect(() => { api.get('/members/bylaws').then(({ data }) => setDoc(data)).catch((e) => setErr(e?.response?.data?.detail || 'Could not load bylaws.')); }, []);

  const download = async () => {
    setDl(true);
    try {
      const { data } = await api.get('/members/bylaws/file', { responseType: 'blob' });
      const url = URL.createObjectURL(data);
      const a = document.createElement('a'); a.href = url; a.download = 'Caring_Sisters_Club_Bylaws.docx'; a.click();
      URL.revokeObjectURL(url);
    } finally { setDl(false); }
  };

  if (err) return <p data-testid="bylaws-error" className="text-[#241019]/60">{err}</p>;
  if (!doc) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div className="grid lg:grid-cols-[240px_1fr] gap-10" data-testid="bylaws-view">
      <aside className="lg:sticky lg:top-28 self-start">
        <p className="eyebrow text-[#B4247E] mb-3">Contents</p>
        <nav className="space-y-1.5 mb-6">
          {doc.sections.map((s, i) => (
            <a key={i} href={`#article-${i}`} className="block text-[13px] text-[#241019]/70 hover:text-[#B4247E] transition-colors leading-snug">{s.title.replace(/^ARTICLE\s+/, '')}</a>
          ))}
        </nav>
        <button data-testid="bylaws-download-btn" onClick={download} disabled={dl} className="btn-magenta rounded-full px-5 py-2.5 text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-60">
          {dl ? <Loader2 className="animate-spin" size={14} /> : <Download size={14} />} Download (.docx)
        </button>
        <p className="text-[11.5px] text-[#241019]/45 mt-3">Updated {fmtDate(doc.updated_at)}. For members only — please don't share outside the Club.</p>
      </aside>
      <article className="bg-white rounded-2xl p-7 md:p-12 border border-[#3B0A2E]/8">
        <header className="text-center mb-10 pb-8 border-b border-[#3B0A2E]/10">
          {doc.intro.map((l, i) => <p key={i} className={i < 2 ? 'font-serif text-[#3B0A2E] text-[26px] font-semibold' : 'text-[13px] text-[#241019]/55 mt-1'}>{l}</p>)}
        </header>
        {doc.sections.map((s, i) => (
          <section key={i} id={`article-${i}`} data-testid={`bylaws-article-${i}`} className="mb-9 scroll-mt-28">
            <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-3">{s.title}</h3>
            {s.paragraphs.map((p, j) => <p key={j} className="text-[14.5px] text-[#241019]/80 leading-relaxed whitespace-pre-line mb-2.5">{p}</p>)}
          </section>
        ))}
      </article>
    </div>
  );
}
