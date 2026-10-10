import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { CreditCard, Loader2, CheckCircle2, AlertTriangle, CalendarCheck } from 'lucide-react';
import { fmtDate } from './fmt';

const money = (n) => `$${Number(n || 0).toFixed(2).replace(/\.00$/, '')}`;
const STATUS = { paid: ['Paid in full', 'bg-green-100 text-green-800'], due: ['Balance due', 'bg-amber-100 text-amber-800'], overdue: ['Overdue', 'bg-red-100 text-red-700'] };
const FLAG = { warning: '2 meetings missed in a row: warning letter', fine: '3 meetings missed in a row: $10 fine added', officer_removal: 'Officer has missed 3 meetings: may be removed from office', termination: '4 or more meetings missed: membership ends in December' };
const ATT = { present: 'text-green-700', absent: 'text-red-600', excused: 'text-[#241019]/50' };

function PayBox({ balance }) {
  const [amt, setAmt] = useState(balance);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const pay = async () => {
    setBusy(true); setErr('');
    try { const { data } = await api.post('/members/dues/checkout', { amount: Number(amt) }); window.location.href = data.url; }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Could not start payment.'); setBusy(false); }
  };
  return (
    <div className="mt-5 flex flex-wrap items-center gap-3">
      <span className="text-[13px] text-[#241019]/60">Pay</span>
      <input data-testid="dues-pay-amount" type="number" min="1" max={balance} step="1" value={amt} onChange={(e) => setAmt(e.target.value)} className="w-28 rounded-full border border-[#3B0A2E]/15 px-4 py-2 text-[14px] focus:outline-none focus:border-[#B4247E]" />
      <button data-testid="dues-pay-btn" onClick={pay} disabled={busy} className="btn-magenta rounded-full px-6 py-2.5 text-[14px] font-semibold flex items-center gap-2 disabled:opacity-60">{busy ? <Loader2 className="animate-spin" size={15} /> : <CreditCard size={15} />} Pay by card</button>
      {err && <p data-testid="dues-pay-error" className="w-full text-red-600 text-[13px]">{err}</p>}
      <p className="w-full text-[12px] text-[#241019]/50">Paying by cash or Zelle? Give it to the Financial Secretary and it will be recorded here.</p>
    </div>
  );
}

export function Standing() {
  const [s, setS] = useState(null);
  const [notice, setNotice] = useState('');
  const load = useCallback(() => api.get('/members/standing').then(({ data }) => setS(data)), []);
  useEffect(() => {
    const sid = new URLSearchParams(window.location.search).get('dues_session');
    if (!sid) { load(); return; }
    window.history.replaceState({}, '', '/members');
    let tries = 0;
    const poll = async () => {
      const { data } = await api.get(`/members/dues/checkout/${sid}`).catch(() => ({ data: {} }));
      if (data.status === 'paid') { setNotice(`Thank you! Your ${money(data.amount)} payment was received.`); load(); }
      else if (++tries < 6) setTimeout(poll, 2000);
      else { setNotice('Your payment is processing. It will appear here shortly.'); load(); }
    };
    poll();
  }, [load]);

  if (!s) return <p className="text-[#241019]/50">Loading…</p>;
  const [label, cls] = STATUS[s.dues_status];
  return (
    <div className="space-y-6" data-testid="standing-view">
      {notice && <p data-testid="dues-notice" className="bg-green-50 text-green-800 rounded-xl px-4 py-3 text-[14px] flex items-center gap-2"><CheckCircle2 size={16} /> {notice}</p>}
      <div className="grid md:grid-cols-[1.3fr_1fr] gap-5">
        <div className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold">{s.year} dues</h3>
            <span data-testid="dues-status" className={`text-[12px] font-semibold px-3 py-1 rounded-full ${cls}`}>{label}</span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            {[['Dues ($10/mo)', s.dues_expected], ['Fees & fines', s.charges], ['Paid', s.paid]].map(([l, v]) => (
              <div key={l} className="rounded-xl bg-[#F7EFE9] py-3"><p className="text-[11.5px] text-[#241019]/55">{l}</p><p className="font-semibold text-[#3B0A2E] text-[17px]">{money(v)}</p></div>
            ))}
          </div>
          <p className="mt-4 text-[15px] text-[#241019]/80">Balance: <b data-testid="dues-balance" className="text-[#B4247E] text-[20px]">{money(s.balance)}</b>{s.credit > 0 && <span className="text-[13px] text-green-700 ml-2">({money(s.credit)} credit)</span>}</p>
          {s.due_date && <p className="text-[12.5px] text-[#241019]/55 mt-1">Due in full by {fmtDate(s.due_date + 'T12:00:00')}</p>}
          {s.balance > 0 && <PayBox balance={s.balance} />}
        </div>
        <div className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
          <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold mb-3">Standing</h3>
          <p data-testid="good-standing" className={`text-[14px] font-semibold flex items-center gap-2 ${s.good_standing ? 'text-green-700' : 'text-red-600'}`}>
            {s.good_standing ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />} {s.good_standing ? 'In good standing: you can vote' : 'Not in good standing'}
          </p>
          <p className="text-[13px] text-[#241019]/60 mt-2">Meetings missed this year: <b>{s.attendance.total_absences}</b> · in a row: <b>{s.attendance.consecutive_absences}</b></p>
          {s.attendance.flags.map((f) => <p key={f} data-testid={`flag-${f}`} className="text-[12.5px] text-red-700 bg-red-50 rounded-lg px-3 py-2 mt-2">{FLAG[f]}</p>)}
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
          <h4 className="font-semibold text-[#3B0A2E] mb-3">Activity</h4>
          {!s.ledger.length ? <p className="text-[13px] text-[#241019]/50">No payments or charges yet.</p> : s.ledger.map((e) => (
            <div key={e.id} className="flex justify-between text-[13px] py-1.5 border-b border-[#3B0A2E]/6 last:border-0">
              <span className="text-[#241019]/75">{fmtDate(e.created_at)} · {e.note}</span>
              <span className={e.direction === 'payment' ? 'text-green-700 font-semibold' : 'text-[#241019]/80'}>{e.direction === 'payment' ? '−' : '+'}{money(e.amount)}</span>
            </div>
          ))}
        </div>
        <div className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
          <h4 className="font-semibold text-[#3B0A2E] mb-3 flex items-center gap-2"><CalendarCheck size={16} className="text-[#B4247E]" /> Meeting attendance</h4>
          {!s.attendance.history.length ? <p className="text-[13px] text-[#241019]/50">No meetings recorded yet this year.</p> : s.attendance.history.slice().reverse().map((h) => (
            <div key={h.meeting_id} className="flex justify-between text-[13px] py-1.5 border-b border-[#3B0A2E]/6 last:border-0">
              <span className="text-[#241019]/75">{fmtDate(h.date + 'T12:00:00')} · {h.title}</span><span className={`capitalize font-semibold ${ATT[h.status]}`}>{h.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
