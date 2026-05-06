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
  getBusinesses:    ()       => request('/businesses/'),
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
  getClients:    ()       => request('/clients/'),
  getClient:     (id)     => request(`/clients/${id}`),
  createClient:  (data)   => request('/clients/', { method: 'POST', body: JSON.stringify(data) }),
  updateClient:  (id, d)  => request(`/clients/${id}`, { method: 'PUT', body: JSON.stringify(d) }),

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
}

export default api
