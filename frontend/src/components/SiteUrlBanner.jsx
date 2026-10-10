import React, { useEffect, useState } from 'react';
import { AlertTriangle, Loader2, Check } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

export const SiteUrlBanner = () => {
  const [state, setState] = useState('loading');
  const { toast } = useToast();
  const origin = window.location.origin;

  useEffect(() => {
    api.get('/admin/settings').then(({ data }) => setState(data.site_url ? 'set' : 'missing')).catch(() => setState('set'));
  }, []);

  const useThis = async () => {
    setState('saving');
    try {
      await api.put('/admin/settings', { site_url: origin });
      setState('saved');
      toast({ title: 'Website address saved', description: `Donor email links now point to ${origin}` });
    } catch (err) {
      setState('missing');
      toast({ title: 'Could not save address', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    }
  };

  if (state === 'loading' || state === 'set') return null;
  if (state === 'saved') {
    return (
      <div className="mb-6 rounded-2xl px-5 py-3 flex items-center gap-2 text-[13.5px]" style={{ background: '#e9f3e6', color: '#3c7a2f' }} data-testid="site-url-banner-saved">
        <Check size={16} /> Email links now use {origin}
      </div>
    );
  }
  return (
    <div className="mb-6 rounded-2xl px-5 py-4 flex flex-col sm:flex-row sm:items-center gap-3 justify-between" style={{ background: '#fdf3e1', border: '1px solid #ecd7a6' }} data-testid="site-url-banner">
      <p className="text-[13.5px] text-[#5c4415] flex items-start gap-2">
        <AlertTriangle size={17} className="shrink-0 mt-0.5 text-[#8a6a2c]" />
        <span><strong>Your website address isn't set.</strong> Buttons in donor emails (receipts, appeals, RSVPs) currently point to the preview site. Save this site's address so donors always land on your live site.</span>
      </p>
      <button onClick={useThis} disabled={state === 'saving'} data-testid="use-site-url-btn"
        className="btn-magenta rounded-full px-5 py-2.5 text-[13px] font-semibold whitespace-nowrap flex items-center gap-2 disabled:opacity-60">
        {state === 'saving' && <Loader2 size={14} className="animate-spin" />} Use {origin.replace('https://', '')}
      </button>
    </div>
  );
};
