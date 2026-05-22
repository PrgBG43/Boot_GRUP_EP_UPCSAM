const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'
const HEALTH_URL = BASE_URL.replace('/api/v1', '')

export class ApiError extends Error {
  constructor(message, { status, details } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

function getToken() {
  return localStorage.getItem('turnix_token')
}

function clearSession() {
  localStorage.removeItem('turnix_token')
  localStorage.removeItem('turnix_user')
  localStorage.removeItem('turnix_active_tenant')
}

function validationMessage(item) {
  if (!item) return null
  if (typeof item === 'string') return item
  if (item.msg) return item.msg
  if (item.detail) return item.detail
  return null
}

function normalizeDetail(detail, status) {
  if (status === 401) return 'La sesión expiró. Inicia sesión nuevamente.'
  if (status === 403) return 'Permiso insuficiente.'
  if (status >= 500) return 'Ocurrió un error en el servidor. Intenta nuevamente.'

  if (detail && Array.isArray(detail)) {
    const first = detail.map(validationMessage).find(Boolean)
    return first || 'Revisa los campos del formulario.'
  }

  if (typeof detail === 'string') return detail
  if (detail && detail.message) return detail.message
  if (detail?.detail) return normalizeDetail(detail.detail, status)

  return 'No fue posible completar la solicitud.'
}

async function parseErrorResponse(res) {
  const payload = await res.json().catch(() => null)
  const message = normalizeDetail(payload?.detail ?? payload, res.status)
  return new ApiError(message, { status: res.status, details: payload?.detail ?? payload })
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  let res
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  } catch {
    throw new ApiError('No se pudo establecer conexión con el servidor.', { status: 0 })
  }

  if (res.status === 401) {
    clearSession()
    window.dispatchEvent(new Event('turnix:unauthorized'))
    throw new ApiError('La sesión expiró. Inicia sesión nuevamente.', { status: 401 })
  }

  if (!res.ok) {
    throw await parseErrorResponse(res)
  }

  if (res.status === 204) return null
  return res.json()
}

async function requestForm(path, formData, options = {}) {
  const token = getToken()
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  let res
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, method: options.method || 'POST', headers, body: formData })
  } catch {
    throw new ApiError('No se pudo establecer conexion con el servidor.', { status: 0 })
  }

  if (res.status === 401) {
    clearSession()
    window.dispatchEvent(new Event('turnix:unauthorized'))
    throw new ApiError('La sesion expiro. Inicia sesion nuevamente.', { status: 401 })
  }

  if (!res.ok) throw await parseErrorResponse(res)
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  health: () => fetch(`${HEALTH_URL}/health`).then(r => r.json()),

  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  getMe: () => request('/auth/me'),

  getBusinesses: (params) => request(`/businesses/?${new URLSearchParams(params || {})}`),
  getMyBusiness: () => request('/businesses/me'),
  getBusiness: (id) => request(`/businesses/${id}`),
  createBusiness: (data) => request('/businesses/', { method: 'POST', body: JSON.stringify(data) }),
  createBusinessWithAdmin: (data) => request('/businesses/with-admin', { method: 'POST', body: JSON.stringify(data) }),
  updateBusiness: (id, data) => request(`/businesses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  activateTenant: (id) => request(`/businesses/${id}/activate`, { method: 'PATCH' }),
  deactivateTenant: (id) => request(`/businesses/${id}/deactivate`, { method: 'PATCH' }),
  archiveTenant: (id) => request(`/businesses/${id}/archive`, { method: 'PATCH' }),
  restoreTenant: (id) => request(`/businesses/${id}/restore`, { method: 'PATCH' }),
  assignPlan: (id, plan) => request(`/businesses/${id}/plan?plan_name=${encodeURIComponent(plan)}`, { method: 'PATCH' }),
  getBusinessUsage: (id) => request(`/businesses/${id}/usage`),

  getStates: () => request('/states/?limit=100'),
  getCities: (stateId) => request(`/cities/?state_id=${encodeURIComponent(stateId)}&limit=500`),
  getPlans: () => request('/plans/'),

  getServices: (params) => request(`/services/?${new URLSearchParams(params || {})}`),
  getService: (id) => request(`/services/${id}`),
  createService: (data) => request('/services/', { method: 'POST', body: JSON.stringify(data) }),
  updateService: (id, data) => request(`/services/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteService: (id) => request(`/services/${id}`, { method: 'DELETE' }),

  getClients: (params) => request(`/clients/?${new URLSearchParams(params || {})}`),
  getClient: (id) => request(`/clients/${id}`),
  createClient: (data) => request('/clients/', { method: 'POST', body: JSON.stringify(data) }),
  updateClient: (id, data) => request(`/clients/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  getAppointments: (params) => request(`/appointments/?${new URLSearchParams(params || {})}`),
  getAppointment: (id) => request(`/appointments/${id}`),
  createAppointment: (data) => request('/appointments/', { method: 'POST', body: JSON.stringify(data) }),
  updateAppointment: (id, data) => request(`/appointments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  cancelAppointment: (id) => request(`/appointments/${id}/cancel`, { method: 'PATCH' }),
  completeAppointment: (id) => request(`/appointments/${id}/complete`, { method: 'PATCH' }),

  getAvailability: (params) => request(`/availability/?${new URLSearchParams(params)}`),

  getConversations: (params) => request(`/conversations/?${new URLSearchParams(params || {})}`),
  getConversation: (id) => request(`/conversations/${id}`),
  getMessages: (id) => request(`/conversations/${id}/messages`),

  getSuperadminDashboard: () => request('/dashboard/superadmin'),
  getTenantDashboard: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/dashboard/tenant${qs}`)
  },
  getStaffDashboard: () => request('/dashboard/staff'),

  getStaff: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/users/staff${qs}`)
  },
  createStaff: (data) => request('/users/staff', { method: 'POST', body: JSON.stringify(data) }),
  updateStaff: (id, data) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  activateStaff: (id) => request(`/users/${id}/activate`, { method: 'PATCH' }),
  deactivateStaff: (id) => request(`/users/${id}/deactivate`, { method: 'PATCH' }),

  getUsers: (params) => request(`/users/?${new URLSearchParams(params || {})}`),
  getUser: (id) => request(`/users/${id}`),
  createUser: (data) => request('/users/', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  resetPassword: (id, data) => request(`/users/${id}/reset-password`, { method: 'PATCH', body: JSON.stringify(data) }),
  activateUser: (id) => request(`/users/${id}/activate`, { method: 'PATCH' }),
  deactivateUser: (id) => request(`/users/${id}/deactivate`, { method: 'PATCH' }),
  deleteUser: (id) => request(`/users/${id}`, { method: 'DELETE' }),

  getTelegramConfig: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/${qs}`)
  },
  getTelegramPublicLink: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/public-link${qs}`)
  },
  updateTelegramConfig: (data, tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/${qs}`, { method: 'PUT', body: JSON.stringify(data) })
  },
  connectTelegramBot: (botToken, tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/connect${qs}`, {
      method: 'POST',
      body: JSON.stringify({ bot_token: botToken }),
    })
  },
  disconnectTelegramBot: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/disconnect${qs}`, { method: 'POST' })
  },
  validateTelegramBot: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/validate${qs}`, {
      method: 'POST',
    })
  },
  uploadTelegramProfilePhoto: (file, tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    const form = new FormData()
    form.append('photo', file)
    return requestForm(`/telegram-config/profile-photo${qs}`, form)
  },
  removeTelegramProfilePhoto: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : ''
    return request(`/telegram-config/profile-photo${qs}`, { method: 'DELETE' })
  },
}

export default api
