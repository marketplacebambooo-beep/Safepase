const API = import.meta.env.VITE_API_URL || ''



export function getToken() {

  return localStorage.getItem('safepass_token')

}



export function setToken(token) {

  localStorage.setItem('safepass_token', token)

}



export function clearToken() {

  localStorage.removeItem('safepass_token')

  localStorage.removeItem('safepass_user')

}



export function getUser() {

  const raw = localStorage.getItem('safepass_user')

  return raw ? JSON.parse(raw) : null

}



export function setUser(user) {

  localStorage.setItem('safepass_user', JSON.stringify(user))

}



async function upload(path, formData) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${API}${path}`, { method: 'POST', headers, body: formData })
  } catch {
    throw new Error('Cannot reach server. Is the backend running on port 8001?')
  }

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : res.statusText
    throw new Error(message || res.statusText)
  }
  return res.json()
}


async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${API}${path}`, { ...options, headers })
  } catch {
    throw new Error('Cannot reach server. Is the backend running on port 8001?')
  }

  const isLogin = path.includes('/auth/login')
  if (res.status === 401 && !isLogin) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : res.statusText
    throw new Error(message || res.statusText)
  }
  if (res.status === 204) return null
  return res.json()
}



export const api = {

  health: () => request('/health'),

  login: (email, password) =>

    request('/api/auth/login/json', { method: 'POST', body: JSON.stringify({ email, password }) }),

  forgotPassword: (email) =>

    request('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),

  resetPassword: (token, new_password) =>

    request('/api/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password }) }),

  changePassword: (current_password, new_password) =>

    request('/api/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password, new_password }) }),

  me: () => request('/api/auth/me'),

  pregnancies: (params = {}) => {

    const qs = new URLSearchParams()

    if (params.risk && params.risk !== 'all') qs.set('risk', params.risk)

    if (params.q) qs.set('q', params.q)

    const query = qs.toString()

    return request(`/api/pregnancies${query ? `?${query}` : ''}`)

  },

  createPregnancy: (data) =>

    request('/api/pregnancies', { method: 'POST', body: JSON.stringify(data) }),

  pregnancy: (id) => request(`/api/pregnancies/${id}`),

  updatePregnancyStatus: (id, status) =>

    request(`/api/pregnancies/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  updatePregnancyCare: (id, data) =>

    request(`/api/pregnancies/${id}/care`, { method: 'PATCH', body: JSON.stringify(data) }),

  addDangerSign: (id, data) =>

    request(`/api/pregnancies/${id}/danger-signs`, { method: 'POST', body: JSON.stringify(data) }),

  visits: (id) => request(`/api/pregnancies/${id}/visits`),

  updateBirthPrep: (id, data) =>

    request(`/api/pregnancies/${id}/birth-prep`, { method: 'PUT', body: JSON.stringify(data) }),

  facilities: () => request('/api/facilities'),

  chws: () => request('/api/chws'),

  referrals: () => request('/api/referrals'),

  createReferral: (data) =>

    request('/api/referrals', { method: 'POST', body: JSON.stringify(data) }),

  updateReferralStatus: (id, status) =>

    request(`/api/referrals/${id}/status?status=${status}`, { method: 'PATCH' }),

  analytics: () => request('/api/analytics/summary'),

  districtAnalytics: () => request('/api/analytics/district'),

  notifications: () => request('/api/notifications'),

  retryNotification: (id) => request(`/api/notifications/${id}/retry`, { method: 'POST' }),

  auditLogs: () => request('/api/audit-logs'),

  languages: () => request('/api/languages'),
  educationSchedule: (id) => request(`/api/pregnancies/${id}/education`),
  sendEducation: (id) => request(`/api/pregnancies/${id}/send-education`, { method: 'POST' }),
  aiInsights: (id) => request(`/api/pregnancies/${id}/ai-insights`),
  refreshAiTriage: (id) => request(`/api/pregnancies/${id}/ai-triage`, { method: 'POST' }),
  aiChat: (message, sessionId) => request('/api/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId ?? null }),
  }),
  aiChatHistory: (sessionId) => request(`/api/ai/chat/history${sessionId ? `?session_id=${sessionId}` : ''}`),
  aiChatSessions: () => request('/api/ai/chat/sessions'),
  createAiChatSession: () => request('/api/ai/chat/sessions', { method: 'POST' }),
  deleteAiChatSession: (id) => request(`/api/ai/chat/sessions/${id}`, { method: 'DELETE' }),
  transcribeAiChat: (file) => {
    const form = new FormData()
    form.append('file', file)
    return upload('/api/ai/chat/transcribe', form)
  },
  attachAiChatFile: (file) => {
    const form = new FormData()
    form.append('file', file)
    return upload('/api/ai/chat/attach', form)
  },
  clearAiChat: () => request('/api/ai/chat/history', { method: 'DELETE' }),
  dashboardSummary: () => request('/api/ai/dashboard-summary'),
  ancCalendar: () => request('/api/anc-calendar'),
  complianceReport: () => request('/api/analytics/compliance'),
  channelsStatus: () => request('/api/channels/status'),

  admin: {

    facilities: () => request('/api/admin/facilities'),

    createFacility: (data) => request('/api/admin/facilities', { method: 'POST', body: JSON.stringify(data) }),

    updateFacility: (id, data) => request(`/api/admin/facilities/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

    users: () => request('/api/admin/users'),

    createUser: (data) => request('/api/admin/users', { method: 'POST', body: JSON.stringify(data) }),

    updateUser: (id, data) => request(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

    chws: () => request('/api/admin/chws'),

    createChw: (data) => request('/api/admin/chws', { method: 'POST', body: JSON.stringify(data) }),

    updateChw: (id, data) => request(`/api/admin/chws/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  },

}

