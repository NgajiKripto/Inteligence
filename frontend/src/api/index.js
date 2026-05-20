import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5001'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

// === Token API ===
export const tokenApi = {
  discover: (data) => api.post('/api/token/discover', data),
  trending: (params) => api.get('/api/token/trending', { params }),
  watchlist: (params) => api.get('/api/token/watchlist', { params }),
  getToken: (tokenId) => api.get(`/api/token/${tokenId}`),
  getMetrics: (tokenId) => api.get(`/api/token/${tokenId}/metrics`),
  getHolders: (tokenId, params) => api.get(`/api/token/${tokenId}/holders`, { params }),
  getRisk: (tokenId) => api.get(`/api/token/${tokenId}/risk`),
  remove: (tokenId) => api.delete(`/api/token/${tokenId}`),
  search: (params) => api.get('/api/token/search', { params }),
}

// === Analysis API ===
export const analysisApi = {
  start: (data) => api.post('/api/analysis/start', data),
  status: (sessionId) => api.get(`/api/analysis/status/${sessionId}`),
  report: (sessionId) => api.get(`/api/analysis/report/${sessionId}`),
  simulate: (data) => api.post('/api/analysis/simulate', data),
  chat: (data) => api.post('/api/analysis/chat', data),
  history: (params) => api.get('/api/analysis/history', { params }),
}

// === Signal API ===
export const signalApi = {
  list: (params) => api.get('/api/signal/list', { params }),
  whaleActivity: (params) => api.get('/api/signal/whale-activity', { params }),
  smartMoney: (params) => api.get('/api/signal/smart-money', { params }),
  sentiment: (params) => api.get('/api/signal/sentiment', { params }),
  newPairs: (params) => api.get('/api/signal/new-pairs', { params }),
  rugCheck: (address, params) => api.get(`/api/signal/rug-check/${address}`, { params }),
}

export default api
