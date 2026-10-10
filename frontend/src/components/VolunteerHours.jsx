import React, { useEffect, useState } from 'react';
import { Loader2, Clock3, CheckCircle2, Trophy, Award } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from '../pages/Events';

const inp = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E] bg-white';
const today = () => new Date().toISOString().slice(0, 10);
const BADGE_STYLE = {
  10: { background: '#f2e6ee', color: '#B4247E' },
  50: { background: '#fdf3e1', color: '#8a6a2c' },
  100: { background: '#3B0A2E', color: '#CBA24B' },
};

export const LogHours = () => {
  const [programs, setPrograms] = useState([]);
  const [form, setForm] = useState({ name: '', email: '', program_id: '', date: today(), hours: '', note: '', leaderboard: false });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { api.get('/programs').then(({ data }) => setPrograms(data.items || [])).catch(() => {}); }, []);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try { await api.post('/volunteer-hours', { ...form, hours: Number(form.hours) }); setDone(true); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };
  const again = () => { setDone(false); setForm((f) => ({ ...f, hours: '', note: '', date: today(), leaderboard: false })); };

  return (
    <section className="py-16 lg:py-20" style={{ background: '#F7EFE9' }} id="log-hours" data-testid="log-hours">
      <div className="max-w-3xl mx-auto px-5 lg:px-8">
        <div className="bg-white rounded-[24px] p-8 lg:p-10 border border-[#3B0A2E]/8">
          {done ? (
            <div className="text-center" data-testid="log-hours-success">
              <CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" />
              <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-1">Thank you for your time!</p>
              <p className="text-[14px] text-[#241019]/65 mb-5">Your hours were submitted. Once our team confirms them, they'll count toward our public volunteer total.</p>
              <button onClick={again} data-testid="log-more-hours-btn" className="text-[14px] font-semibold text-[#B4247E]">Log more hours</button>
            </div>
          ) : (
            <form onSubmit={submit}>
              <h2 className="font-serif text-[28px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><Clock3 size={24} className="text-[#B4247E]" /> Log My Hours</h2>
              <p className="text-[14px] text-[#241019]/65 mb-5">Already volunteering with us? Record your time so we can celebrate it in our impact report.</p>
              <div className="grid sm:grid-cols-2 gap-4">
                <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Full Name</label><input required value={form.name} onChange={set('name')} className={inp} data-testid="hours-name-input" /></div>
                <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Email</label><input required type="email" value={form.email} onChange={set('email')} className={inp} data-testid="hours-email-input" /></div>
                <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Program</label>
                  <select required value={form.program_id} onChange={set('program_id')} className={inp} data-testid="hours-program-select">
                    <option value="">Choose a program…</option>
                    {programs.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Date</label><input required type="date" max={today()} value={form.date} onChange={set('date')} className={inp} data-testid="hours-date-input" /></div>
                  <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Hours</label><input required type="number" min={0.25} max={24} step={0.25} value={form.hours} onChange={set('hours')} className={inp} data-testid="hours-hours-input" /></div>
                </div>
              </div>
              <div className="mt-4"><label className="text-[13px] font-semibold text-[#3B0A2E]">What did you do? (optional)</label><input value={form.note} onChange={set('note')} className={inp} data-testid="hours-note-input" /></div>
              <label className="flex items-center gap-2 mt-4 text-[13px] text-[#3B0A2E] cursor-pointer">
                <input type="checkbox" checked={form.leaderboard} onChange={(e) => setForm({ ...form, leaderboard: e.target.checked })} className="accent-[#B4247E] w-4 h-4" data-testid="hours-leaderboard-checkbox" />
                Show me on the "Top Volunteers" list (first name and last initial only)
              </label>
              {error && <p className="text-[13px] text-red-600 mt-3" data-testid="hours-error">{error}</p>}
              <button type="submit" disabled={busy} data-testid="hours-submit-btn" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px] mt-5 flex items-center gap-2 disabled:opacity-60">
                {busy && <Loader2 size={16} className="animate-spin" />} Submit Hours
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
};

export const Leaderboard = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/volunteer-hours/leaderboard').then(({ data }) => setD(data)).catch(() => {}); }, []);
  if (!d || !d.items.length) return null;
  return (
    <section className="py-16 lg:py-20" data-testid="volunteer-leaderboard">
      <div className="max-w-3xl mx-auto px-5 lg:px-8">
        <h2 className="font-serif text-[30px] lg:text-[36px] text-[#3B0A2E] font-semibold mb-2 flex items-center gap-3"><Trophy size={28} className="text-[#CBA24B]" /> Top Volunteers {d.year}</h2>
        <p className="text-[#241019]/65 text-[14.5px] mb-7">Celebrating the sisters who give their time. Thank you!</p>
        <ol className="bg-white rounded-2xl border border-[#3B0A2E]/8 divide-y divide-[#3B0A2E]/8">
          {d.items.map((v, i) => (
            <li key={`${v.name}-${i}`} className="flex items-center gap-4 px-6 py-4" data-testid="leaderboard-row">
              <span className="w-9 h-9 rounded-full flex items-center justify-center font-bold text-[14px]" style={i < 3 ? { background: ['#CBA24B', '#c0c4cc', '#c98a5a'][i], color: '#fff' } : { background: '#faf2f7', color: '#3B0A2E' }}>{i + 1}</span>
              <span className="flex-1 font-semibold text-[#3B0A2E] text-[15px] flex items-center gap-2" data-testid="leaderboard-name">{v.name}
                {v.badge && <span title={`${v.badge}-hour all-time badge`} data-testid="leaderboard-badge" className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full" style={BADGE_STYLE[v.badge]}><Award size={12} /> {v.badge}h</span>}
              </span>
              <span className="font-serif text-[20px] font-bold text-[#B4247E]" data-testid="leaderboard-hours">{v.hours}h</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
};

export const VolunteerImpact = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/volunteer-hours/summary').then(({ data }) => setD(data)).catch(() => {}); }, []);
  if (!d || !d.total_hours) return null;
  const max = Math.max(...d.by_program.map((b) => b.hours));
  return (
    <section className="pb-20" data-testid="volunteer-impact">
      <div className="max-w-5xl mx-auto px-5 lg:px-8">
        <div className="rounded-[24px] p-8 lg:p-10 grid md:grid-cols-[1fr_1.4fr] gap-10 items-center" style={{ background: 'linear-gradient(160deg,#3B0A2E,#4d1240)' }}>
          <div>
            <Clock3 className="text-[#CBA24B] mb-3" size={32} />
            <p className="font-serif text-[#CBA24B] text-[56px] font-bold leading-none" data-testid="volunteer-total-hours">{d.total_hours.toLocaleString()}</p>
            <p className="text-[#F7EFE9]/85 text-[15px] mt-2">volunteer hours given by <strong data-testid="volunteer-count">{d.volunteers}</strong> sister{d.volunteers === 1 ? '' : 's'}</p>
          </div>
          <div className="space-y-3">
            {d.by_program.map((b) => (
              <div key={b.program} data-testid="volunteer-program-row">
                <div className="flex justify-between text-[13.5px] text-[#F7EFE9] mb-1"><span>{b.program}</span><span className="font-bold">{b.hours}h</span></div>
                <div className="h-2.5 rounded-full bg-white/10 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${(b.hours / max) * 100}%`, background: '#CBA24B' }} /></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
