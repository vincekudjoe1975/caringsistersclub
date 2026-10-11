import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { Html5Qrcode } from 'html5-qrcode';
import { Search, QrCode, Check, Undo2, Minus, Plus, X, Loader2 } from 'lucide-react';

function Scanner({ onCode, onClose }) {
  const ref = useRef(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    const qr = new Html5Qrcode('qr-reader');
    ref.current = qr;
    let last = '';
    qr.start({ facingMode: 'environment' }, { fps: 10, qrbox: 230 }, (text) => { if (text !== last) { last = text; onCode(text); setTimeout(() => { last = ''; }, 3000); } }, () => {})
      .catch(() => setErr('Camera not available. Please allow camera access, or search by name instead.'));
    return () => { qr.isScanning && qr.stop().catch(() => {}); };
  }, [onCode]);
  return (
    <div data-testid="qr-scanner" className="fixed inset-0 bg-black/85 z-50 flex flex-col items-center justify-center p-4">
      <button data-testid="qr-close" onClick={onClose} className="absolute top-4 right-4 text-white"><X size={28} /></button>
      <div id="qr-reader" className="w-full max-w-sm rounded-2xl overflow-hidden bg-black" />
      <p className="text-white/80 text-[14px] mt-4 text-center">{err || "Point the camera at the sister's check-in code"}</p>
    </div>
  );
}

function Row({ r, onCheck, onUndo }) {
  const [g, setG] = useState(r.guests || r.rsvp_guests || 0);
  const inn = r.status === 'present';
  return (
    <div data-testid={`ci-row-${r.user_id}`} className={`flex items-center gap-3 px-4 py-3 border-b border-[#3B0A2E]/8 ${inn ? 'bg-green-50' : 'bg-white'}`}>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-[15px] text-[#3B0A2E] truncate">{r.name}</p>
        <p className="text-[12px] text-[#241019]/55">{inn ? `Checked in${r.guests ? ` +${r.guests} guest${r.guests === 1 ? '' : 's'}` : ''}` : r.status === 'absent' ? 'Marked absent' : r.status === 'excused' ? 'Excused' : r.rsvp ? `RSVP: ${r.rsvp}${r.rsvp_guests ? ` +${r.rsvp_guests}` : ''}` : 'No RSVP'}</p>
      </div>
      {inn ? (
        <button data-testid={`ci-undo-${r.user_id}`} onClick={() => onUndo(r.user_id)} className="text-[#241019]/50 p-2"><Undo2 size={18} /></button>
      ) : (
        <>
          <div className="flex items-center gap-1">
            <button data-testid={`ci-guest-minus-${r.user_id}`} onClick={() => setG(Math.max(0, g - 1))} className="w-8 h-8 rounded-full border border-[#3B0A2E]/15 flex items-center justify-center"><Minus size={14} /></button>
            <span data-testid={`ci-guests-${r.user_id}`} className="w-6 text-center text-[14px]">{g}</span>
            <button data-testid={`ci-guest-plus-${r.user_id}`} onClick={() => setG(Math.min(20, g + 1))} className="w-8 h-8 rounded-full border border-[#3B0A2E]/15 flex items-center justify-center"><Plus size={14} /></button>
          </div>
          <button data-testid={`ci-check-${r.user_id}`} onClick={() => onCheck(r.user_id, g)} className="btn-magenta rounded-full px-4 py-2.5 text-[14px] font-semibold flex items-center gap-1"><Check size={16} /> Check in</button>
        </>
      )}
    </div>
  );
}

export default function CheckIn() {
  const [sp, setSp] = useSearchParams();
  const [list, setList] = useState(null);
  const [mid, setMid] = useState(sp.get('m') || '');
  const [sheet, setSheet] = useState(null);
  const [q, setQ] = useState('');
  const [scan, setScan] = useState(false);
  const [flash, setFlash] = useState('');
  const [err, setErr] = useState('');
  useEffect(() => {
    api.get('/admin/members/checkin').then(({ data }) => {
      setList(data.meetings);
      if (!mid && data.meetings.length) setMid((data.meetings.find((m) => m.date >= data.today) || data.meetings[data.meetings.length - 1]).id);
    }).catch((e) => setErr(e?.response?.status === 401 ? 'login' : 'Staff access only.'));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const load = useCallback(() => mid && api.get(`/admin/members/checkin/${mid}`).then(({ data }) => setSheet(data)), [mid]);
  useEffect(() => { load(); if (mid) setSp({ m: mid }, { replace: true }); }, [mid, load, setSp]);
  const show = (t) => { setFlash(t); setTimeout(() => setFlash(''), 2500); };
  const check = async (body) => {
    try { const { data } = await api.post(`/admin/members/checkin/${mid}`, body); show(`${data.name} checked in`); load(); }
    catch (ex) { show(ex?.response?.data?.detail || 'Check-in failed'); }
  };
  const onCode = useCallback((code) => check({ code }), [mid]); // eslint-disable-line react-hooks/exhaustive-deps
  const undo = async (uid) => { await api.delete(`/admin/members/checkin/${mid}/${uid}`); load(); };
  const finish = async () => {
    if (!window.confirm('Mark everyone who has not checked in as absent? Attendance warnings and fines will be applied.')) return;
    const { data } = await api.post(`/admin/members/checkin/${mid}/finish`); show(`${data.marked_absent} marked absent`); load();
  };
  if (err) return <div className="p-10 text-center"><p data-testid="ci-error" className="text-[#241019]/70 mb-4">{err === 'login' ? 'Please sign in as staff to use door check-in.' : err}</p>{err === 'login' && <Link to="/login" className="btn-magenta rounded-full px-6 py-3 font-semibold">Staff sign in</Link>}</div>;
  if (!list) return <div className="p-16 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  const rows = (sheet?.rows || []).filter((r) => r.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="min-h-screen bg-[#F7EFE9] pb-28" data-testid="checkin-page">
      <header className="csc-plum-deep-bg text-[#F7EFE9] px-4 pt-5 pb-4 sticky top-0 z-10">
        <div className="flex items-center justify-between mb-3"><p className="font-serif text-[20px] font-semibold">Door check-in</p><Link to="/admin" className="text-[12.5px] text-[#F7EFE9]/70">Admin</Link></div>
        <select data-testid="ci-meeting-select" value={mid} onChange={(e) => setMid(e.target.value)} className="w-full rounded-xl px-3 py-2.5 text-[14px] text-[#241019] mb-3">
          {!list.length && <option value="">No meetings in the next 30 days</option>}
          {list.map((m) => <option key={m.id} value={m.id}>{new Date(m.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} · {m.title}</option>)}
        </select>
        {sheet && (
          <div className="grid grid-cols-3 gap-2 text-center mb-3">
            {[['Checked in', sheet.counts.present, 'ci-present'], ['Guests', sheet.counts.guests, 'ci-guests'], ['Headcount', sheet.counts.headcount, 'ci-headcount']].map(([l, v, t]) => (
              <div key={l} className="bg-white/10 rounded-xl py-2"><p className="text-[11px] text-[#F7EFE9]/70">{l}</p><p data-testid={t} className="font-semibold text-[20px]">{v}</p></div>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <label className="relative flex-1"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#241019]/40" />
            <input data-testid="ci-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name" className="w-full rounded-xl pl-9 pr-3 py-2.5 text-[15px] text-[#241019]" /></label>
          <button data-testid="ci-scan-btn" onClick={() => setScan(true)} className="rounded-xl bg-[#CBA24B] text-[#3B0A2E] px-4 font-semibold flex items-center gap-1.5"><QrCode size={18} /> Scan</button>
        </div>
      </header>
      {flash && <div data-testid="ci-flash" className="fixed top-3 left-1/2 -translate-x-1/2 z-50 bg-[#3B0A2E] text-white px-5 py-2.5 rounded-full text-[14px] shadow-lg">{flash}</div>}
      <div>{rows.map((r) => <Row key={`${r.user_id}-${r.status}`} r={r} onCheck={(uid, guests) => check({ user_id: uid, guests })} onUndo={undo} />)}</div>
      {sheet && <div className="fixed bottom-0 inset-x-0 p-4 bg-white border-t border-[#3B0A2E]/10">
        <button data-testid="ci-finish-btn" onClick={finish} className="w-full rounded-full py-3.5 font-semibold bg-[#3B0A2E] text-white">{sheet.meeting.finished_at ? 'Finish again (mark remaining absent)' : 'Finish: mark the rest absent'}</button>
      </div>}
      {scan && <Scanner onCode={onCode} onClose={() => { setScan(false); load(); }} />}
    </div>
  );
}
