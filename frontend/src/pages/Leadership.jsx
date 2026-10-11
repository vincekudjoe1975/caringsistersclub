import React, { useState, useEffect } from 'react';
import { board as mockBoard, governance, org } from '../mock/mock';
import { api } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { LeaderCard, LeaderModal } from '../components/LeaderModal';
import { ShieldCheck, FileCheck2 } from 'lucide-react';

export const DEFAULT_LEADERS = mockBoard.map((m, i) => ({ id: `default-${i}`, name: m.name, role: m.role, group: 'board', intro: m.bio, bio: m.bio, photo_url: m.photo }));

function Group({ kicker, title, list, all, onOpen, start }) {
  if (!list.length) return null;
  return (
    <div className="mb-20 last:mb-0">
      <div className="max-w-2xl mb-12">
        <p className="eyebrow text-[#B4247E] mb-4">{kicker}</p>
        <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">{title}</h2>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {list.map((m, i) => (
          <Reveal key={m.id} delay={(i % 3) * 100}>
            <LeaderCard m={m} testid={`leader-card-${start + i}`} onOpen={() => onOpen(all.indexOf(m))} />
          </Reveal>
        ))}
      </div>
    </div>
  );
}

export default function Leadership() {
  const [team, setTeam] = useState(null);
  const [open, setOpen] = useState(null);
  useEffect(() => {
    api.get('/leaders').then(({ data }) => setTeam(data.items.length ? data.items : DEFAULT_LEADERS)).catch(() => setTeam(DEFAULT_LEADERS));
  }, []);
  const list = team || [];
  const boardList = list.filter((m) => m.group !== 'executive');
  const execList = list.filter((m) => m.group === 'executive');
  const all = [...boardList, ...execList];
  return (
    <div>
      <PageHero
        kicker="Governance & Oversight"
        title="Executive & Leadership Team"
        subtitle="Meet the founders and board who steward our mission with transparency, accountability, and heart — guiding the sisterhood forward every day."
      />

      <section className="py-20 lg:py-24" data-testid="leadership-team">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <Group kicker="Board of Directors" title="The women guiding our vision" list={boardList} all={all} onOpen={setOpen} start={0} />
          <Group kicker="Executive Team" title="Leading our work every day" list={execList} all={all} onOpen={setOpen} start={boardList.length} />
        </div>
      </section>
      {open !== null && <LeaderModal list={all} index={open} setIndex={setOpen} onClose={() => setOpen(null)} />}

      <section className="py-20 lg:py-24" style={{ background: '#F7EFE9' }}>
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="flex items-center gap-3 mb-12">
            <ShieldCheck className="text-[#B4247E]" size={30} />
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">Governance Policies</h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {governance.map((g, i) => (
              <Reveal key={g.title} delay={(i % 2) * 100}>
                <div className="card-hover rounded-2xl p-7 h-full flex gap-4 bg-white" style={{ border: '1px solid rgba(59,10,46,0.08)' }}>
                  <FileCheck2 className="text-[#CBA24B] shrink-0" size={24} />
                  <div>
                    <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-2">{g.title}</h3>
                    <p className="text-[#241019]/70 text-[14.5px] leading-relaxed">{g.desc}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
          <p className="text-[#241019]/55 text-[13px] italic mt-8">
            {org.name} maintains formal governance policies in line with nonprofit best practices.
          </p>
        </div>
      </section>
    </div>
  );
}
