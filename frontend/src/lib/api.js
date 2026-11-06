import axios from 'axios';

// Same-origin API: every host (apex, www, installed app) proxies /api, so the session cookie stays first-party.
export const BACKEND_URL = typeof window !== 'undefined' ? window.location.origin : process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
});

// Build a full URL for a media item served by the backend
export const mediaSrc = (urlPath) => `${BACKEND_URL}${urlPath}`;
