const BASE_URL   = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const HEALTH_URL = BASE_URL.replace('/api/v1', '')

function getToken() {
  return localStorage.getItem('turnix_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (res.status === 401) {
    localStorage.removeItem('turnix_token')
    localStorage.removeItem('turnix_user')
    window.location.href = '/login'
    return
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Error en la petición')
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Health
  health: () => fetch(`${HEALTH_URL}/health`).then(r => r.json()),

  // Auth
  login: (email, password) => request('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password })
  }),
  getMe: () => request('/auth/me'),

  // Negocios (tenants) – solo superadmin para lista
  getBusinesses:    (params) => request(`/businesses/?${new URLSearchParams(params || {})}`),

  // Ubicación (departamentos y ciudades)
  getStates: () => request('/states/?limit=100'),
  getCities: (stateId) => request(`/cities/?state_id=${stateId}&limit=500`),

  getMyBusiness:    ()       => request('/businesses/me'),
  getBusiness:      (id)     => request(`/businesses/${id}`),
  createBusiness:   (data)   => request('/businesses/', { method: 'POST', body: JSON.stringify(data) }),
  updateBusiness:   (id, d)  => request(`/businesses/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  activateTenant:   (id)     => request(`/businesses/${id}/activate`, { method: 'PATCH' }),
  deactivateTenant: (id)     => request(`/businesses/${id}/deactivate`, { method: 'PATCH' }),
  assignPlan:       (id, plan) => request(`/businesses/${id}/plan?plan_name=${plan}`, { method: 'PATCH' }),

  // Planes
  getPlans: () => request('/plans/'),

  // Servicios
  getServices:   (params) => request(`/services/?${new URLSearchParams(params || {})}`),
  getService:    (id)     => request(`/services/${id}`),
  createService: (data)   => request('/services/', { method: 'POST', body: JSON.stringify(data) }),
  updateService: (id, d)  => request(`/services/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  deleteService: (id)     => request(`/services/${id}`, { method: 'DELETE' }),

  // Clientes
  getClients:    (params)  => request(`/clients/?${new URLSearchParams(params || {})}`),
  getClient:     (id)      => request(`/clients/${id}`),
  createClient:  (data)    => request('/clients/', { method: 'POST', body: JSON.stringify(data) }),
  updateClient:  (id, d)   => request(`/clients/${id}`, { method: 'PUT', body: JSON.stringify(d) }),

  // Citas
  getAppointments:    (params) => request(`/appointments/?${new URLSearchParams(params || {})}`),
  getAppointment:     (id)     => request(`/appointments/${id}`),
  createAppointment:  (data)   => request('/appointments/', { method: 'POST', body: JSON.stringify(data) }),
  updateAppointment:  (id, d)  => request(`/appointments/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  cancelAppointment:  (id)     => request(`/appointments/${id}/cancel`, { method: 'PATCH' }),
  completeAppointment:(id)     => request(`/appointments/${id}/complete`, { method: 'PATCH' }),

  // Disponibilidad (público para bot)
  getAvailability: (params) => request(`/availability/?${new URLSearchParams(params)}`),

  // Conversaciones
  getConversations: () => request('/conversations/'),
  getConversation:  (id) => request(`/conversations/${id}`),
  getMessages:      (id) => request(`/conversations/${id}/messages`),

  // Dashboard
  getSuperadminDashboard: () => request('/dashboard/superadmin'),
  getTenantDashboard: (tenant_id) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : ''
    return request(`/dashboard/tenant${qs}`)
  },
  getStaffDashboard: () => request('/dashboard/staff'),

  // Usuarios / Personal
  getStaff:        (tenant_id) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : ''
    return request(`/users/staff${qs}`)
  },
  createStaff:     (data)   => request('/users/', { method: 'POST', body: JSON.stringify(data) }),
  updateStaff:     (id, d)  => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  activateStaff:   (id)     => request(`/users/${id}/activate`, { method: 'PATCH' }),
  deactivateStaff: (id)     => request(`/users/${id}/deactivate`, { method: 'PATCH' }),

  // Usuarios completos (superadmin / tenant_admin)
  getUsers:          (params)  => request(`/users/?${new URLSearchParams(params || {})}`),
  getUser:           (id)      => request(`/users/${id}`),
  createUser:        (data)    => request('/users/', { method: 'POST', body: JSON.stringify(data) }),
  updateUser:        (id, d)   => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  activateUser:      (id)      => request(`/users/${id}/activate`, { method: 'PATCH' }),
  deactivateUser:    (id)      => request(`/users/${id}/deactivate`, { method: 'PATCH' }),
  deleteUser:        (id)      => request(`/users/${id}`, { method: 'DELETE' }),

  // Configuración de Telegram
  getTelegramConfig:    (tenant_id) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : ''
    return request(`/telegram-config/${qs}`)
  },
  updateTelegramConfig: (data, tenant_id) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : ''
    return request(`/telegram-config/${qs}`, { method: 'PUT', body: JSON.stringify(data) })
  },
  validateTelegramToken: (bot_token, tenant_id) => {
    const qs = tenant_id ? `?tenant_id=${tenant_id}` : ''
    return request(`/telegram-config/validate${qs}`, {
      method: 'POST',
      body: JSON.stringify({ bot_token }),
    })
  },

  // Negocios con admin integrado (superadmin)
  createBusinessWithAdmin: (data) => request('/businesses/with-admin', { method: 'POST', body: JSON.stringify(data) }),
}

export default api
