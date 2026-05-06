const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Error en la petición')
  }
  if (res.status === 204) return null
  return res.json()
}

// ── Negocios ──────────────────────────────────
export const api = {
  // Health
  health: () => fetch('http://localhost:8000/health').then(r => r.json()),

  // Negocios (tenants)
  getBusinesses:   ()       => request('/businesses/'),
  getBusiness:     (id)     => request(`/businesses/${id}`),
  createBusiness:  (data)   => request('/businesses/', { method: 'POST', body: JSON.stringify(data) }),
  updateBusiness:  (id, d)  => request(`/businesses/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  deleteBusiness:  (id)     => request(`/businesses/${id}`, { method: 'DELETE' }),

  // Servicios
  getServices:     (params) => request(`/services/?${new URLSearchParams(params || {})}`),
  getService:      (id)     => request(`/services/${id}`),
  createService:   (data)   => request('/services/', { method: 'POST', body: JSON.stringify(data) }),
  updateService:   (id, d)  => request(`/services/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  deleteService:   (id)     => request(`/services/${id}`, { method: 'DELETE' }),

  // Clientes
  getClients:      ()       => request('/clients/'),
  getClient:       (id)     => request(`/clients/${id}`),
  createClient:    (data)   => request('/clients/', { method: 'POST', body: JSON.stringify(data) }),
  updateClient:    (id, d)  => request(`/clients/${id}`, { method: 'PUT', body: JSON.stringify(d) }),

  // Citas
  getAppointments: (params) => request(`/appointments/?${new URLSearchParams(params || {})}`),
  getAppointment:  (id)     => request(`/appointments/${id}`),
  createAppointment: (data) => request('/appointments/', { method: 'POST', body: JSON.stringify(data) }),
  updateAppointment: (id,d) => request(`/appointments/${id}`, { method: 'PUT', body: JSON.stringify(d) }),
  cancelAppointment: (id)   => request(`/appointments/${id}/cancel`, { method: 'PATCH' }),
  completeAppointment:(id)  => request(`/appointments/${id}/complete`, { method: 'PATCH' }),

  // Disponibilidad
  getAvailability: (params) => request(`/availability/?${new URLSearchParams(params)}`),

  // Conversaciones
  getConversations: ()      => request('/conversations/'),
  getConversation:  (id)    => request(`/conversations/${id}`),
  getMessages:      (id)    => request(`/conversations/${id}/messages`),
}

export default api
