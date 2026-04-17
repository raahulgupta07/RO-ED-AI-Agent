import { auth } from './stores/auth.svelte';

const BASE = '/api';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Pre-request: refresh Keycloak token if about to expire
  await auth.ensureValidToken();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (auth.token) {
    headers['Authorization'] = `Bearer ${auth.token}`;
  }

  // Only set Content-Type for non-FormData bodies
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers, redirect: 'manual' });

  // Handle redirect (FastAPI trailing slash redirect strips auth header)
  if (res.status === 307 || res.status === 308 || res.status === 301 || res.status === 302) {
    const redirectUrl = res.headers.get('location');
    if (redirectUrl) {
      const retryRes = await fetch(redirectUrl, { ...options, headers });
      if (retryRes.ok) return retryRes.json();
      if (retryRes.status === 401) { auth.logout(); throw new Error('Unauthorized'); }
      const err = await retryRes.json().catch(() => ({ detail: retryRes.statusText }));
      throw new Error(err.detail || retryRes.statusText);
    }
  }

  if (res.status === 401) {
    // Try one refresh before giving up
    if (auth.isKeycloak && auth.refreshTokenValue) {
      const refreshed = await auth.refreshAccessToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${auth.token}`;
        const retry = await fetch(`${BASE}${path}`, { ...options, headers });
        if (retry.ok) return retry.json();
      }
    }
    auth.logout();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  return res.json();
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<any>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

  me: () => request<any>('/auth/me'),

  getAuthConfig: () => fetch(`${BASE}/auth/config`).then(r => r.json()),

  // Jobs
  listJobs: (limit = 50) => request<any[]>(`/jobs?limit=${limit}`),
  getJob: (jobId: string) => request<any>(`/jobs/${jobId}`),
  deleteJob: (jobId: string) => request<any>(`/jobs/${jobId}`, { method: 'DELETE' }),
  uploadPdf: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<any>('/jobs/upload', { method: 'POST', body: form });
  },

  // Data
  listItems: (jobId?: string) => request<any[]>(`/data/items${jobId ? `?job_id=${jobId}` : ''}`),
  listDeclarations: (jobId?: string) => request<any[]>(`/data/declarations${jobId ? `?job_id=${jobId}` : ''}`),
  search: (query: string, pdfName?: string) =>
    request<any[]>(`/data/search?query=${encodeURIComponent(query)}${pdfName ? `&pdf_name=${encodeURIComponent(pdfName)}` : ''}`),
  searchPdfs: () => request<string[]>('/data/search/pdfs'),
  stats: () => request<any>('/data/stats'),

  // Users
  listUsers: () => request<any[]>('/users/'),
  createUser: (data: any) => request<any>('/users/', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id: number, data: any) => request<any>(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteUser: (id: number) => request<any>(`/users/${id}`, { method: 'DELETE' }),
  activityLogs: (limit = 200) => request<any[]>(`/users/activity-logs?limit=${limit}`),

  // Groups
  listGroups: () => request<any[]>('/groups/'),
  getGroup: (id: number) => request<any>(`/groups/${id}`),
  createGroup: (data: any) => request<any>('/groups/', { method: 'POST', body: JSON.stringify(data) }),
  updateGroup: (id: number, data: any) => request<any>(`/groups/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteGroup: (id: number) => request<any>(`/groups/${id}`, { method: 'DELETE' }),
  assignUserGroup: (userId: number, groupId: number | null) =>
    request<any>(`/groups/assign/${userId}`, { method: 'PUT', body: JSON.stringify({ group_id: groupId }) }),

  // Settings — Keycloak
  getKeycloakSettings: () => request<any>('/settings/keycloak'),
  saveKeycloakSettings: (data: any) => request<any>('/settings/keycloak', { method: 'PUT', body: JSON.stringify(data) }),
  testKeycloakConnection: (data: any) => request<any>('/settings/keycloak/test', { method: 'POST', body: JSON.stringify(data) }),

  // v2 page extractions + confidence
  getJobPages: (jobId: string) => request<any[]>(`/jobs/${jobId}/pages`),
  getJobConfidence: (jobId: string) => request<any>(`/jobs/${jobId}/confidence`),

  // Corrections (few-shot learning)
  submitCorrection: (data: any) =>
    request<any>('/corrections/', { method: 'POST', body: JSON.stringify(data) }),

  // Health
  health: () => request<any>('/health'),
};
