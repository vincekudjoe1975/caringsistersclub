import axios from 'axios';

// Same-origin API: every host (apex, www, installed app) proxies /api, so the session cookie stays first-party.
export const BACKEND_URL = typeof window !== 'undefined' ? window.location.origin : process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
});

export const PREVIEW_KEY = 'csc_admin_preview';
export const getPreview = () => { try { return JSON.parse(sessionStorage.getItem(PREVIEW_KEY)) || null; } catch { return null; } };
api.interceptors.request.use((cfg) => {
  const p = getPreview();
  if (p) { cfg.headers['X-Preview-Level'] = p.level; cfg.headers['X-Preview-Mode'] = p.mode; }
  return cfg;
});

// Build a full URL for a media item served by the backend
export const mediaSrc = (urlPath) => `${BACKEND_URL}${urlPath}`;
