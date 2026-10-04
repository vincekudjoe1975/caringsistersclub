import axios from 'axios';

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
});

// Build a full URL for a media item served by the backend
export const mediaSrc = (urlPath) => `${BACKEND_URL}${urlPath}`;
