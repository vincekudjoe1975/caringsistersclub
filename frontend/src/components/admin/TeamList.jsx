import React, { useState } from 'react';
import { ShieldCheck, UserRound } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';

const Tag = ({ children, tone, testid }) => (
  <span data-testid={testid} className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full whitespace-nowrap" style={tone === 'admin' ? { background: '#1f7a4d', color: '#fff' } : tone === 'owner' ? { background: '#3B0A2E', color: '#fff' } : { background: '#f0ece4', color: '#8a6d2f' }}>{children}</span>
);

function Row({ u, me, onAsk }) {
  const staff = u.role === 'admin';
  return (
    <div data-testid={`team-row-${u.user_id}`} className="flex items-center justify-between gap-3 p-4">
      <div className="flex items-center gap-3 min-w-0">
        {u.picture ? <img loading="lazy" decoding="async" src={u.picture} alt="" className="w-9 h-9 rounded-full" referrerPolicy="no-referrer" /> : <span className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold shrink-0" style={{ background: '#B4247E' }}>{(u.name || u.email || '?').charAt(0)}</span>}
        <div className="min-w-0">
          <p className="text-[14px] text-[#3B0A2E] font-semibold truncate">{u.name || u.email}{u.user_id === me && <span className="text-[#241019]/45 font-normal"> (you)</span>}</p>
          <p className="text-[12px] text-[#241019]/55 truncate">{u.email}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {staff ? <Tag tone={u.is_owner ? 'owner' : 'admin'} testid={`team-tag-${u.user_id}`}>{u.is_owner ? 'Owner' : 'Admin'}</Tag> : <Tag testid={`team-tag-${u.user_id}`}>Member · portal only</Tag>}
        {staff && !u.is_owner && u.user_id !== me && (
          <button data-testid={`team-make-member-${u.user_id}`} onClick={() => onAsk(u, 'member')} className="rounded-full px-3 py-1.5 text-[12px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] flex items-center gap-1 transition-colors"><UserRound size={13} /> Change to member</button>
        )}
        {!staff && (
          <button data-testid={`team-make-staff-${u.user_id}`} onClick={() => onAsk(u, 'admin')} className="rounded-full px-3 py-1.5 text-[12px] font-semibold text-[#1f7a4d] hover:bg-[#1f7a4d]/10 flex items-center gap-1 transition-colors"><ShieldCheck size={13} /> Make staff</button>
        )}
      </div>
    </div>
  );
}

const COPY = {
  member: (u) => ({ t: `Change ${u.name || u.email} to a member?`, d: 'She will lose access to Admin right away. She keeps the member portal only.', b: 'Change to member' }),
  admin: (u) => ({ t: `Give ${u.name || u.email} Admin access?`, d: 'She will be able to open the back office and change site content, members and donations. Only do this for Club staff.', b: 'Make staff' }),
};

export function TeamList({ users, me, onConfirm }) {
  const [ask, setAsk] = useState(null);
  const staff = users.filter((u) => u.role === 'admin');
  const others = users.filter((u) => u.role !== 'admin');
  const c = ask && COPY[ask.to](ask.u);
  const section = (list, testid, empty) => (
    <div data-testid={testid} className="bg-white rounded-2xl border border-[#3B0A2E]/8 divide-y divide-[#3B0A2E]/8">
      {list.length ? list.map((u) => <Row key={u.user_id} u={u} me={me} onAsk={(x, to) => setAsk({ u: x, to })} />) : <p className="p-4 text-[13px] text-[#241019]/55">{empty}</p>}
    </div>
  );
  return (
    <div>
      <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-1">Staff with Admin access</h3>
      <p className="text-[12.5px] text-[#241019]/60 mb-4">Only these people can open the back office.</p>
      {section(staff, 'team-staff-list', 'No staff yet.')}
      <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mt-10 mb-1">Member accounts</h3>
      <p className="text-[12.5px] text-[#241019]/60 mb-4">People who signed up but haven't applied yet. They can't open Admin. Approve memberships under Members.</p>
      {section(others, 'team-member-list', 'No member accounts waiting.')}
      <AlertDialog open={!!ask} onOpenChange={(o) => !o && setAsk(null)}>
        <AlertDialogContent data-testid="team-confirm-dialog">
          {c && <>
            <AlertDialogHeader><AlertDialogTitle>{c.t}</AlertDialogTitle><AlertDialogDescription>{c.d}</AlertDialogDescription></AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel data-testid="team-confirm-cancel">Cancel</AlertDialogCancel>
              <AlertDialogAction data-testid="team-confirm-ok" onClick={() => { onConfirm(ask.u, ask.to); setAsk(null); }}>{c.b}</AlertDialogAction>
            </AlertDialogFooter>
          </>}
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
