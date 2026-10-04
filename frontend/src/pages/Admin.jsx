import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api, mediaSrc } from '../lib/api';
import Logo from '../components/Logo';
import AdminSubmissions from './AdminSubmissions';
import AdminDonations from './AdminDonations';
import AdminTeam from './AdminTeam';
import { useToast } from '../hooks/use-toast';
import { LogOut, UploadCloud, Trash2, Loader2, Image as ImageIcon, Users, FileText, CalendarDays, ExternalLink, Home, Images, Inbox, DollarSign, ShieldCheck, Clock } from 'lucide-react';

const TABS = [
  { key: 'gallery', label: 'Gallery Photos', icon: ImageIcon, accept: 'image/*', titleLabel: 'Caption', subLabel: '' },
  { key: 'board', label: 'Leadership', icon: Users, accept: 'image/*', titleLabel: 'Full Name', subLabel: 'Role / Title' },
  { key: 'event', label: 'Event Images', icon: CalendarDays, accept: 'image/*', titleLabel: 'Event Name', subLabel: 'Date / Location' },
  { key: 'document', label: 'Documents', icon: FileText, accept: '.pdf,application/pdf', titleLabel: 'Document Title', subLabel: 'Year / Label' },
];

export default function Admin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [tab, setTab] = useState('gallery');
  const [view, setView] = useState('media');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [subtitle, setSubtitle] = useState('');

  const current = TABS.find((t) => t.key === tab);

  const load = useCallback(async (category) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/media?category=${category}`);
      setItems(data);
    } catch (e) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(tab);
    setFile(null); setTitle(''); setSubtitle('');
  }, [tab, load]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) { toast({ title: 'Please choose a file', variant: 'destructive' }); return; }
    const fd = new FormData();
    fd.append('file', file);
    fd.append('category', tab);
    if (title) fd.append('title', title);
    if (subtitle) fd.append('subtitle', subtitle);
    setUploading(true);
    try {
      await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast({ title: 'Uploaded successfully' });
      setFile(null); setTitle(''); setSubtitle('');
      e.target.reset?.();
      load(tab);
    } catch (err) {
      toast({ title: 'Upload failed', description: err?.response?.data?.detail || 'Please try again', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/media/${id}`);
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast({ title: 'Deleted' });
    } catch (e) {
      toast({ title: 'Delete failed', variant: 'destructive' });
    }
  };

  if (user === null) {
    return <div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin text-[#B4247E]" size={36} /></div>;
  }

  if (user && user.role !== 'admin') {
    return (
      <div className="csc-hero-gradient min-h-screen flex items-center justify-center px-5">
        <div className="bg-white rounded-3xl p-10 max-w-md text-center" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
          <span className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
            <Clock size={30} className="text-white" />
          </span>
          <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3">Access pending approval</h1>
          <p className="text-[#241019]/65 text-[14.5px] mb-7">
            Thanks for signing in{user?.name ? `, ${user.name}` : ''}. Your account needs to be approved by an existing administrator before you can access the dashboard.
          </p>
          <div className="flex justify-center gap-3">
            <button onClick={() => navigate('/')} className="rounded-full px-6 py-2.5 font-semibold text-[14px]" style={{ border: '1px solid rgba(59,10,46,0.2)', color: '#3B0A2E' }}>View Site</button>
            <button onClick={logout} className="btn-magenta rounded-full px-6 py-2.5 font-semibold text-[14px] flex items-center gap-2"><LogOut size={14} /> Sign Out</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: '#F7EFE9' }}>
      {/* Top bar */}
      <header className="csc-plum-deep-bg">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 h-[72px] flex items-center justify-between">
          <Logo variant="light" compact />
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="text-[#F7EFE9]/80 hover:text-[#F7EFE9] text-[13.5px] flex items-center gap-1.5">
              <Home size={15} /> View Site
            </button>
            {user && user.picture && <img src={user.picture} alt="" className="w-8 h-8 rounded-full" referrerPolicy="no-referrer" />}
            <button onClick={logout} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5">
              <LogOut size={14} /> Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-5 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="font-serif text-[32px] text-[#3B0A2E] font-semibold">Content Manager</h1>
          <p className="text-[#241019]/65 text-[14.5px] mt-1">Welcome{user?.name ? `, ${user.name}` : ''}. Manage media and review form submissions.</p>
        </div>

        {/* View switch */}
        <div className="inline-flex flex-wrap gap-1 p-1.5 rounded-full mb-8 bg-white border border-[#3B0A2E]/8">
          {[
            { k: 'media', l: 'Media Library', icon: Images },
            { k: 'inbox', l: 'Form Submissions', icon: Inbox },
            { k: 'donations', l: 'Donations', icon: DollarSign },
            { k: 'team', l: 'Team Access', icon: ShieldCheck },
          ].map((v) => {
            const Icon = v.icon;
            return (
              <button key={v.k} onClick={() => setView(v.k)}
                className={`px-5 py-2 rounded-full text-[14px] font-semibold flex items-center gap-2 transition-all ${view === v.k ? 'text-white' : 'text-[#3B0A2E]'}`}
                style={view === v.k ? { background: '#3B0A2E' } : {}}>
                <Icon size={16} /> {v.l}
              </button>
            );
          })}
        </div>

        {view === 'inbox' ? (
          <AdminSubmissions />
        ) : view === 'donations' ? (
          <AdminDonations />
        ) : view === 'team' ? (
          <AdminTeam currentUserId={user?.user_id} />
        ) : (
        <>
        {/* Tabs */}
        <div className="flex flex-wrap gap-2 mb-8">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-5 py-2.5 rounded-full text-[14px] font-semibold flex items-center gap-2 transition-all ${tab === t.key ? 'text-white' : 'text-[#3B0A2E] bg-white hover:bg-[#f2e6ee]'}`}
                style={tab === t.key ? { background: '#B4247E' } : { border: '1px solid rgba(59,10,46,0.1)' }}>
                <Icon size={16} /> {t.label}
              </button>
            );
          })}
        </div>

        <div className="grid lg:grid-cols-[360px_1fr] gap-8 items-start">
          {/* Upload form */}
          <form onSubmit={handleUpload} className="bg-white rounded-2xl p-7 border border-[#3B0A2E]/8">
            <h2 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-5">Upload {current.label}</h2>
            <label className="block border-2 border-dashed border-[#3B0A2E]/20 rounded-xl p-6 text-center cursor-pointer hover:border-[#B4247E] transition-colors mb-5">
              <UploadCloud className="mx-auto text-[#B4247E] mb-2" size={28} />
              <span className="text-[13px] text-[#241019]/70 block">{file ? file.name : `Click to choose a ${tab === 'document' ? 'PDF' : 'image'}`}</span>
              <input type="file" accept={current.accept} className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </label>
            <div className="space-y-4">
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">{current.titleLabel}</label>
                <input value={title} onChange={(e) => setTitle(e.target.value)} className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              {current.subLabel && (
                <div>
                  <label className="text-[13px] font-semibold text-[#3B0A2E]">{current.subLabel}</label>
                  <input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
                </div>
              )}
            </div>
            <button type="submit" disabled={uploading} className="btn-magenta rounded-full w-full py-3 font-semibold mt-6 flex items-center justify-center gap-2 disabled:opacity-60">
              {uploading ? <><Loader2 className="animate-spin" size={16} /> Uploading…</> : <><UploadCloud size={16} /> Upload</>}
            </button>
          </form>

          {/* Items list */}
          <div>
            {loading ? (
              <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>
            ) : items.length === 0 ? (
              <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8">
                <p className="text-[#241019]/50">No {current.label.toLowerCase()} uploaded yet.</p>
              </div>
            ) : tab === 'document' ? (
              <div className="space-y-3">
                {items.map((it) => (
                  <div key={it.id} className="bg-white rounded-xl p-4 border border-[#3B0A2E]/8 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: '#faf2f7' }}><FileText size={20} className="text-[#B4247E]" /></span>
                      <div>
                        <p className="font-semibold text-[#3B0A2E] text-[14.5px]">{it.title || it.original_name}</p>
                        <p className="text-[#241019]/50 text-[12px]">{it.subtitle} &middot; {(it.size / 1024).toFixed(0)} KB</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <a href={mediaSrc(it.url)} target="_blank" rel="noreferrer" className="text-[#B4247E] hover:text-[#D14FA0] p-2"><ExternalLink size={17} /></a>
                      <button onClick={() => handleDelete(it.id)} className="text-red-500 hover:text-red-700 p-2"><Trash2 size={17} /></button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {items.map((it) => (
                  <div key={it.id} className="bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 group">
                    <div className="relative h-48">
                      <img src={mediaSrc(it.url)} alt={it.title || ''} className="w-full h-full object-cover" />
                      <button onClick={() => handleDelete(it.id)} className="absolute top-2 right-2 w-9 h-9 rounded-full bg-white/90 flex items-center justify-center text-red-500 hover:bg-white opacity-0 group-hover:opacity-100 transition-opacity">
                        <Trash2 size={16} />
                      </button>
                    </div>
                    {(it.title || it.subtitle) && (
                      <div className="p-4">
                        {it.title && <p className="font-semibold text-[#3B0A2E] text-[14.5px]">{it.title}</p>}
                        {it.subtitle && <p className="text-[#B4247E] text-[12.5px]">{it.subtitle}</p>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        </>
        )}
      </div>
    </div>
  );
}
