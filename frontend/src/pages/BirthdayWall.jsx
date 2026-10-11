import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Avatar } from '../components/members/Avatar';
import { Loader2, Printer, ArrowLeft, Cake } from 'lucide-react';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export default function BirthdayWall() {
  const { uid } = useParams();
  const [w, setW] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.get(`/members/birthdays/${uid}/wall`).then(({ data }) => setW(data)).catch((e) => setErr(e?.response?.status === 401 || e?.response?.status === 403 ? 'Please sign in to the member portal to see this card.' : 'Card not found.')); }, [uid]);
  if (err) return <div className="min-h-screen flex items-center justify-center p-8 text-center"><p data-testid="wall-error" className="text-[#241019]/70">{err} <Link to="/members" className="text-[#B4247E] font-semibold">Member portal</Link></p></div>;
  if (!w) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  const first = (w.name || 'Sister').split(' ')[0];
  return (
    <div className="min-h-screen bg-[#F7EFE9] py-10 px-4 print:bg-white print:py-0" data-testid="birthday-wall-page">
      <div className="max-w-3xl mx-auto flex justify-between mb-5 print:hidden">
        <Link to="/members" data-testid="wall-back" className="text-[13px] font-semibold text-[#B4247E] flex items-center gap-1"><ArrowLeft size={14} /> Member portal</Link>
        <button data-testid="wall-print-btn" onClick={() => window.print()} className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Printer size={14} /> Save or print</button>
      </div>
      <div className="max-w-3xl mx-auto rounded-[28px] overflow-hidden relative print:rounded-none" style={{ background: 'linear-gradient(160deg,#3B0A2E 0%,#5e1247 55%,#7a1a5c 100%)', WebkitPrintColorAdjust: 'exact', printColorAdjust: 'exact' }}>
        <div className="absolute -right-20 -top-20 w-72 h-72 rounded-full opacity-30" style={{ background: 'radial-gradient(circle,#CBA24B,transparent 70%)' }} />
        <div className="absolute -left-16 bottom-10 w-56 h-56 rounded-full opacity-20" style={{ background: 'radial-gradient(circle,#D14FA0,transparent 70%)' }} />
        <div className="relative px-8 md:px-14 pt-12 pb-8 text-center">
          <div className="flex justify-center mb-4"><div className="rounded-full p-1.5" style={{ background: 'linear-gradient(135deg,#CBA24B,#f0d999)' }}><Avatar name={w.name} src={w.picture} size={96} /></div></div>
          <p className="eyebrow text-[#CBA24B] mb-2 flex items-center justify-center gap-2"><Cake size={14} /> {w.month ? `${MONTHS[w.month - 1]} ${w.day || ''}, ` : ''}{w.year}</p>
          <h1 data-testid="wall-title" className="font-serif text-[#F7EFE9] text-4xl sm:text-5xl font-semibold">Happy Birthday, {first}!</h1>
          <p className="text-[#f3dfe9]/85 text-[15px] mt-3 max-w-md mx-auto">With love from your sisters of the Caring Sisters Club</p>
        </div>
        <div className="relative px-6 md:px-12 pb-12">
          {!w.wishes.length ? <p data-testid="wall-empty" className="text-center text-[#F7EFE9]/75 py-8">No wishes yet. Be the first to send {first} some love from the birthdays card.</p> : (
            <div className="columns-1 sm:columns-2 gap-4 [&>*]:mb-4" data-testid="wall-wishes">
              {w.wishes.map((x, i) => (
                <div key={x.id} data-testid={`wall-wish-${x.id}`} className="break-inside-avoid bg-white rounded-2xl p-5" style={{ transform: `rotate(${(i % 3) - 1}deg)` }}>
                  <p className="text-[14.5px] text-[#241019]/85 leading-relaxed whitespace-pre-line">{x.body}</p>
                  <div className="flex items-center gap-2 mt-3"><Avatar name={x.author_name} src={x.author_picture} size={26} /><p className="text-[12.5px] font-semibold text-[#B4247E]">{x.author_name}</p></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
