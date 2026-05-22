import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY         = 'turnix_token'
const USER_KEY          = 'turnix_user'
const ACTIVE_TENANT_KEY = 'turnix_active_tenant'

export function AuthProvider({ children }) {
  const [token, setToken]     = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser]       = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY)) } catch { return null }
  })
  const [activeTenant, setActiveTenantState] = useState(() => {
    try { return JSON.parse(localStorage.getItem(ACTIVE_TENANT_KEY)) } catch { return null }
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const handler = () => {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(ACTIVE_TENANT_KEY)
      setToken(null)
      setUser(null)
      setActiveTenantState(null)
    }
    window.addEventListener('turnix:unauthorized', handler)
    return () => window.removeEventListener('turnix:unauthorized', handler)
  }, [])

  const setActiveTenant = useCallback((tenant) => {
    if (tenant) {
      localStorage.setItem(ACTIVE_TENANT_KEY, JSON.stringify(tenant))
    } else {
      localStorage.removeItem(ACTIVE_TENANT_KEY)
    }
    setActiveTenantState(tenant)
  }, [])

  const login = useCallback(async (email, password) => {
    let res
    try {
      res = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
    } catch {
      throw new Error('No se pudo establecer conexión con el servidor.')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      if (res.status === 401) throw new Error('Correo electrónico o contraseña incorrectos.')
      if (res.status === 403) throw new Error(err.detail || 'Permiso insuficiente.')
      throw new Error(err.detail || 'No fue posible iniciar sesión.')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    const userData = {
      id: data.user_id,
      email: data.email,
      role: data.role,
      tenant_id: data.tenant_id,
      tenant_name: data.tenant_name,
    }
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    setToken(data.access_token)
    setUser(userData)
    // Limpiar tenant activo al hacer login nuevo
    localStorage.removeItem(ACTIVE_TENANT_KEY)
    setActiveTenantState(null)
    return userData
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(ACTIVE_TENANT_KEY)
    setToken(null)
    setUser(null)
    setActiveTenantState(null)
  }, [])

  const isAuthenticated = !!token && !!user
  const isSuperadmin    = user?.role === 'superadmin'
  const isTenantAdmin   = user?.role === 'tenant_admin'
  const isStaff         = user?.role === 'staff'

  // Tenant efectivo para llamadas a la API
  const activeTenantId   = isSuperadmin ? (activeTenant?.id   ?? null) : user?.tenant_id
  const activeTenantName = isSuperadmin ? (activeTenant?.name ?? null) : user?.tenant_name

  return (
    <AuthContext.Provider value={{
      token, user, loading, isAuthenticated,
      isSuperadmin, isTenantAdmin, isStaff,
      activeTenant, activeTenantId, activeTenantName, setActiveTenant,
      login, logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}

