import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'turnix_token'
const USER_KEY  = 'turnix_user'

export function AuthProvider({ children }) {
  const [token, setToken]     = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser]       = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY)) } catch { return null }
  })
  const [loading, setLoading] = useState(false)

  const login = useCallback(async (email, password) => {
    const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Credenciales incorrectas')
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
    return userData
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const isAuthenticated = !!token && !!user
  const isSuperadmin    = user?.role === 'superadmin'
  const isTenantAdmin   = user?.role === 'tenant_admin'
  const isStaff         = user?.role === 'staff'

  return (
    <AuthContext.Provider value={{ token, user, loading, isAuthenticated, isSuperadmin, isTenantAdmin, isStaff, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
