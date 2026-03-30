export const API = import.meta.env.VITE_API_URL || 'https://agent-job-1.onrender.com';

export const getToken = () => sessionStorage.getItem('jat');
export const setToken = t => sessionStorage.setItem('jat', t);
export const getUser = () => { try { return JSON.parse(sessionStorage.getItem('jau') || 'null'); } catch { return null; } };
export const setUser = u => sessionStorage.setItem('jau', JSON.stringify(u));
export const clearAuth = () => { sessionStorage.removeItem('jat'); sessionStorage.removeItem('jau'); };

export async function api(path, opts = {}) {
  const tok = getToken();
  const hdrs = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (tok) hdrs['Authorization'] = `Bearer ${tok}`;
  const r = await fetch(API + path, { ...opts, headers: hdrs });
  if (r.status === 401) { clearAuth(); window.location.href = '/'; return null; }
  return r;
}
