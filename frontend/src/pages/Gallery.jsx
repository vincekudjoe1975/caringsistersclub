import React, { useState } from 'react';
import { gallery } from '../mock/mock';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

export default function Gallery() {
  const [idx, setIdx] = useState(null);
  const open = idx !== null;
  const go = (dir) => setIdx((prev) => (prev + dir + gallery.length) % gallery.length);

  return (
    <div>
      <PageHero
        kicker="Impact Media Gallery"
        title="Moments from our sisterhood"
        subtitle="A look at the summits, service drives, and celebrations that show our impact in action."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="columns-1 sm:columns-2 lg:columns-3 gap-5 [&>*]:mb-5">
            {gallery.map((g, i) => (
              <Reveal key={i} delay={(i % 3) * 80}>
                <button onClick={() => setIdx(i)} className="block w-full img-zoom rounded-2xl overflow-hidden relative group">
                  <img src={g.src} alt={g.caption} className={`w-full object-cover ${g.tall ? 'h-[420px]' : 'h-[290px]'}`} />
                  <div className="absolute inset-0 flex items-end p-5 opacity-0 group-hover:opacity-100 transition-opacity" style={{ background: 'linear-gradient(transparent 50%, rgba(41,6,31,0.8))' }}>
                    <p className="text-[#F7EFE9] text-[14px] font-medium text-left">{g.caption}</p>
                  </div>
                </button>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {open && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.92)' }} onClick={() => setIdx(null)}>
          <button className="absolute top-6 right-6 text-[#F7EFE9] hover:text-[#CBA24B]" onClick={() => setIdx(null)}><X size={32} /></button>
          <button className="absolute left-4 md:left-10 text-[#F7EFE9] hover:text-[#CBA24B]" onClick={(e) => { e.stopPropagation(); go(-1); }}><ChevronLeft size={40} /></button>
          <div className="max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            <img src={gallery[idx].src} alt={gallery[idx].caption} className="w-full max-h-[78vh] object-contain rounded-xl" />
            <p className="text-center text-[#F7EFE9]/85 mt-4 font-serif italic text-[17px]">{gallery[idx].caption}</p>
          </div>
          <button className="absolute right-4 md:right-10 text-[#F7EFE9] hover:text-[#CBA24B]" onClick={(e) => { e.stopPropagation(); go(1); }}><ChevronRight size={40} /></button>
        </div>
      )}
    </div>
  );
}
