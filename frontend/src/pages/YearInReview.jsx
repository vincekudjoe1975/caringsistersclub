import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2, Heart, Clock3, Users, BookOpen, UserPlus, HandHeart, Link2, Check } from 'lucide-react';
import { api, BACKEND_URL } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { TestimonialCard } from '../components/TestimonialCard';

const num = (n) => Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 1 });

function Stat({ icon: Icon, value, label, id, delay }) {
  return (
    <Reveal delay={delay}>
      <div className="bg-white rounded-2xl p-7 border border-[#3B0A2E]/8 h-full card-hover" data-testid={id}>
        <Icon size={26} className="text-[#B4247E] mb-4" />
        <p className="font-serif text-[40px] lg:text-[48px] text-[#3B0A2E] font-bold leading-none">{value}</p>
        <p className="text-[#241019]/60 text-[13.5px] mt-2">{label}</p>
      </div>
    </Reveal>
  );
}

export function ShareBar({ url, text, testid = 'yir' }) {
  const [copied, setCopied] = useState(false);
  const e = encodeURIComponent;
  const links = [
    ['Facebook', `https://www.facebook.com/sharer/sharer.php?u=${e(url)}`],
    ['X', `https://twitter.com/intent/tweet?text=${e(text)}&url=${e(url)}`],
    ['LinkedIn', `https://www.linkedin.com/sharing/share-offsite/?url=${e(url)}`],
    ['WhatsApp', `https://wa.me/?text=${e(`${text} ${url}`)}`],
    ['Email', `mailto:?subject=${e(text)}&body=${e(url)}`],
  ];
  const copy = async () => { try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (err) { console.error('Copy failed', err); } };
  return (
    <div className="flex flex-wrap gap-2.5 justify-center" data-testid={`${testid}-share-bar`}>
      {links.map(([n, href]) => (
        <a key={n} href={href} target="_blank" rel="noopener noreferrer" data-testid={`${testid}-share-${n.toLowerCase()}`}
          className="px-5 py-2.5 rounded-full text-[13.5px] font-semibold text-[#3B0A2E] bg-white border border-[#3B0A2E]/12 hover:border-[#B4247E] hover:text-[#B4247E] transition-colors">{n}</a>
      ))}
      <button onClick={copy} data-testid={`${testid}-copy-link-btn`} className="btn-magenta px-5 py-2.5 rounded-full text-[13.5px] font-semibold flex items-center gap-1.5">
        {copied ? <Check size={15} /> : <Link2 size={15} />} {copied ? 'Link copied' : 'Copy link'}
      </button>
    </div>
  );
}

export default function YearInReview() {
  const { year } = useParams();
  const [d, setD] = useState(undefined);
  useEffect(() => { api.get(`/year-in-review/${encodeURIComponent(year)}`).then(({ data }) => setD(data)).catch(() => setD(null)); }, [year]);

  if (d === undefined) return <div className="pt-40 pb-20 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;
  if (d === null) return (
    <div>
      <PageHero kicker="Year in Review" title={`${year} is coming soon`} subtitle="Our Year in Review for this year has not been published yet." />
      <div className="py-16 text-center" data-testid="yir-not-found"><Link to="/" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px]">Back to Home</Link></div>
    </div>
  );

  return (
    <div data-testid="year-in-review">
      <PageHero kicker="Year in Review" title={`${d.year}: A year of sisterhood`} subtitle="Every gift, every hour, every story. Here is what we built together this year." />
      <section className="py-16 lg:py-20">
        <div className="max-w-6xl mx-auto px-5 lg:px-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <Stat icon={Heart} value={`$${num(Math.round(d.donations_total))}`} label={`raised across ${num(d.gifts)} gifts`} id="yir-donations" delay={0} />
          <Stat icon={Users} value={num(d.donors)} label="generous donors" id="yir-donors" delay={80} />
          <Stat icon={Clock3} value={num(d.volunteer_hours)} label="volunteer hours given" id="yir-hours" delay={160} />
          <Stat icon={HandHeart} value={num(d.volunteers)} label="volunteers who showed up" id="yir-volunteers" delay={240} />
          <Stat icon={UserPlus} value={num(d.signups)} label={`program sign-ups${d.enrolled ? ` · ${num(d.enrolled)} enrolled` : ''}`} id="yir-signups" delay={320} />
          <Stat icon={BookOpen} value={num(d.stories)} label="member stories shared" id="yir-stories" delay={400} />
        </div>
      </section>
      {d.featured_stories.length > 0 && (
        <section className="py-16 lg:py-20" style={{ background: '#F7EFE9' }} data-testid="yir-featured-stories">
          <div className="max-w-6xl mx-auto px-5 lg:px-8">
            <h2 className="font-serif text-[30px] lg:text-[38px] text-[#3B0A2E] font-semibold mb-10">In their own words</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-7">
              {d.featured_stories.map((t, i) => <Reveal key={i} delay={(i % 3) * 100}><TestimonialCard t={{ ...t, role: t.role || t.program }} /></Reveal>)}
            </div>
          </div>
        </section>
      )}
      <section className="py-16 lg:py-20 text-center">
        <div className="max-w-3xl mx-auto px-5 lg:px-8">
          <h2 className="font-serif text-[28px] text-[#3B0A2E] font-semibold mb-2">Share our year</h2>
          <p className="text-[#241019]/65 text-[15px] mb-7">Help more sisters find us by sharing this page.</p>
          <ShareBar url={`${BACKEND_URL}/api/share/year-in-review/${d.year}`} text={`See what The Caring Sisters Club achieved together in ${d.year}!`} />
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Link to={`/donate?amount=${d.ask_amount || 50}&src=yir-page-${d.year}`} onClick={() => api.post(`/yir/${d.year}/click`).catch(() => {})} data-testid="yir-donate-link" className="btn-gold rounded-full px-7 py-3 font-semibold text-[14px] flex items-center gap-2"><Heart size={15} /> Help us do it again: give ${d.ask_amount || 50}</Link>
            <Link to="/volunteer" className="rounded-full px-7 py-3 font-semibold text-[14px] text-[#3B0A2E] border border-[#3B0A2E]/15">Volunteer</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
