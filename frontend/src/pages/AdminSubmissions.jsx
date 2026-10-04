import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, Trash2, Mail, MailOpen, HandHeart, Users, MessageSquare, CalendarCheck, Heart } from 'lucide-react';

const TYPES = [
  { key: 'volunteer', label: 'Volunteers', icon: HandHeart },
  { key: 'member', label: 'Memberships', icon: Users },
  { key: 'contact', label: 'Contact', icon: MessageSquare },
  { key: 'rsvp', label: 'Event RSVPs', icon: CalendarCheck },
  { key: 'donation', label: 'Donations', icon: Heart },
];

function fieldLabel(k) {
  return k.charAt(0).toUpperCase() + k.slice(1).replace(/_/g, ' ');
}

export default function AdminSubmissions() {
  const { toast } = useToast();
  const [type, setType] = useState('volunteer');
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(false);

  const loadCounts = useCallback(async () => {
    try {
      const { data } = await api.get('/submissions/counts');
      setCounts(data);
    } catch (e) { /* ignore */ }
  }, []);

  const load = useCallback(async (t) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/submissions?type=${t}`);
      setItems(data);
    } catch (e) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCounts(); }, [loadCounts]);
  useEffect(() => { load(type); }, [type, load]);

  const markRead = async (id) => {
    try {
      await api.patch(`/submissions/${id}/read`);
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read: true } : i)));
      loadCounts();
    } catch (e) { /* ignore */ }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/submissions/${id}`);
      setItems((prev) => prev.filter((i) => i.id !== id));
      loadCounts();
      toast({ title: 'Deleted' });
    } catch (e) {
      toast({ title: 'Delete failed', variant: 'destructive' });
    }
  };

  return (
    <div className="grid lg:grid-cols-[260px_1fr] gap-8 items-start">
      {/* Type list */}
      <div className="bg-white rounded-2xl p-3 border border-[#3B0A2E]/8">
        {TYPES.map((t) => {
          const Icon = t.icon;
          const c = counts[t.key] || { total: 0, unread: 0 };
          const active = type === t.key;
          return (
            <button key={t.key} onClick={() => setType(t.key)}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-[14px] font-semibold mb-1 transition-all ${active ? 'text-white' : 'text-[#3B0A2E] hover:bg-[#f2e6ee]'}`}
              style={active ? { background: '#B4247E' } : {}}>
              <span className="flex items-center gap-2.5"><Icon size={17} /> {t.label}</span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full ${active ? 'bg-white/25' : 'bg-[#f2e6ee] text-[#B4247E]'}`}>
                {c.unread > 0 ? `${c.unread} new` : c.total}
              </span>
            </button>
          );
        })}
      </div>

      {/* Items */}
      <div>
        {loading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8">
            <p className="text-[#241019]/50">No submissions yet.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {items.map((it) => (
              <div key={it.id} className={`bg-white rounded-2xl p-6 border ${it.read ? 'border-[#3B0A2E]/8' : 'border-[#B4247E]/40'}`}>
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-2">
                    {!it.read && <span className="w-2 h-2 rounded-full" style={{ background: '#B4247E' }} />}
                    <p className="font-serif text-[18px] text-[#3B0A2E] font-semibold">
                      {it.data?.name || it.data?.email || 'Submission'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11.5px] text-[#241019]/45">{new Date(it.created_at).toLocaleString()}</span>
                    <button onClick={() => markRead(it.id)} title={it.read ? 'Read' : 'Mark read'} className="text-[#B4247E] hover:text-[#D14FA0] p-1.5">
                      {it.read ? <MailOpen size={16} /> : <Mail size={16} />}
                    </button>
                    <button onClick={() => remove(it.id)} className="text-red-500 hover:text-red-700 p-1.5"><Trash2 size={16} /></button>
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
                  {Object.entries(it.data || {}).map(([k, v]) => (
                    v !== '' && v != null && (
                      <div key={k} className="text-[13.5px]">
                        <span className="text-[#241019]/45">{fieldLabel(k)}: </span>
                        <span className="text-[#3B0A2E]">{String(v)}</span>
                      </div>
                    )
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
