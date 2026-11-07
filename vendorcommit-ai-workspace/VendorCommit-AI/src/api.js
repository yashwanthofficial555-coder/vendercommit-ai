const API_URL = import.meta.env.VITE_API_URL || '/api/v1';
const TOKEN_KEY = 'vendorcommit_access_token';

export const authStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: token => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request(path, options = {}) {
  const token = authStore.get();
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (response.status === 401 && !path.includes('/auth/login')) {
    authStore.clear();
    window.dispatchEvent(new Event('vendorcommit:unauthorized'));
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = body.errors?.[0]?.msg || body.detail || message; } catch { /* safe fallback */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

const query = params => {
  const search = new URLSearchParams(Object.entries(params).filter(([,v]) => v !== undefined && v !== null && v !== ''));
  return search.size ? `?${search}` : '';
};

export const api = {
  login: (email, password) => request('/auth/login', { method:'POST', body:JSON.stringify({email,password}) }),
  me: () => request('/auth/me'),
  dashboard: () => request('/dashboard/executive'),
  deadlines: days => request(`/dashboard/deadlines${query({days})}`),
  suppliers: (params={}) => request(`/suppliers${query({page_size:100,...params})}`),
  supplier: id => request(`/suppliers/${id}`),
  createSupplier: supplier => request('/suppliers', {method:'POST',body:JSON.stringify(supplier)}),
  updateSupplier: (id,supplier) => request(`/suppliers/${id}`, {method:'PATCH',body:JSON.stringify(supplier)}),
  deleteSupplier: id => request(`/suppliers/${id}`, {method:'DELETE'}),
  supplierStatus: (id,status) => request(`/suppliers/${id}/status`, {method:'PATCH',body:JSON.stringify({status})}),
  performance: id => request(`/suppliers/${id}/performance`),
  commitments: (params={}) => request(`/commitments${query({page_size:100,...params})}`),
  createCommitment: commitment => request('/commitments', {method:'POST',body:JSON.stringify(commitment)}),
  updateCommitment: (id,commitment) => request(`/commitments/${id}`, {method:'PATCH',body:JSON.stringify(commitment)}),
  verifyCommitment: (id,note) => request(`/commitments/${id}/verify`, {method:'POST',body:JSON.stringify({note})}),
  deleteCommitment: id => request(`/commitments/${id}`, {method:'DELETE'}),
  interactions: (params={}) => request(`/interactions${query({page_size:100,...params})}`),
  createInteraction: interaction => request('/interactions', {method:'POST',body:JSON.stringify(interaction)}),
  updateInteraction: (id,interaction) => request(`/interactions/${id}`, {method:'PATCH',body:JSON.stringify(interaction)}),
  deleteInteraction: id => request(`/interactions/${id}`, {method:'DELETE'}),
  retainMemory: memory => request('/memory/retain', {method:'POST',body:JSON.stringify(memory)}),
  recallMemory: (supplierId,q='') => request(`/memory/recall/${supplierId}${query({query:q})}`),
  memoryStatus: () => request('/memory/status'),
  memoryHealth: supplierId => request(`/memory/health${query({supplier_id:supplierId})}`),
  memoryInsights: supplierId => request(`/memory/insights/${supplierId}`),
  compareMemory: (supplierId,scenario) => request(`/memory/compare/${supplierId}${query({scenario})}`),
  retryMemory: id => request(`/memory/${id}/retry`, {method:'POST'}),
};
