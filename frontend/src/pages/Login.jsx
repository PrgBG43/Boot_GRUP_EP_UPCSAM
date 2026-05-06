import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import './Login.css'

export default function Login() {
  const { login } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()
  const from      = location.state?.from?.pathname || '/'

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState(null)
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-brand">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="40" height="40" rx="10" fill="#6c3fc5"/>
            <path d="M12 20C12 20 14 14 20 14C26 14 28 20 28 20C28 20 26 26 20 26C14 26 12 20 12 20Z" stroke="white" strokeWidth="2" fill="none"/>
            <circle cx="20" cy="20" r="3" fill="white"/>
          </svg>
          <span className="login-brand-name">Turnix</span>
        </div>
        <h1 className="login-title">Bienvenido a<br/><strong>Turnix</strong></h1>
        <p className="login-subtitle">
          Plataforma SaaS para la gestión inteligente de citas en negocios del sector de cuidado personal.
        </p>
        <div className="login-features">
          <div className="feature-item">
            <span className="feature-icon">✓</span>
            <span>Multi-tenant con aislamiento total</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">✓</span>
            <span>Gestión de citas en tiempo real</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">✓</span>
            <span>Bot de Telegram integrado</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">✓</span>
            <span>Planes freemium con límites inteligentes</span>
          </div>
        </div>
      </div>

      <div className="login-right">
        <div className="login-card">
          <div className="login-card-header">
            <h2>Iniciar sesión</h2>
            <p>Ingresa tus credenciales para acceder al panel</p>
          </div>

          {error && (
            <div className="login-error">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 6a.75.75 0 01.75.75v3a.75.75 0 01-1.5 0v-3A.75.75 0 018 7zm0-2.5a1 1 0 110 2 1 1 0 010-2z"/>
              </svg>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="usuario@ejemplo.com"
                required
                autoComplete="email"
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>
            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? (
                <span className="btn-loading">
                  <span className="spinner-sm"></span>
                  Verificando…
                </span>
              ) : 'Ingresar al panel'}
            </button>
          </form>

          <div className="login-demo-hint">
            <p className="demo-label">Usuarios de demostración</p>
            <div className="demo-credentials">
              <div className="demo-row" onClick={() => { setEmail('admin@turnix.demo'); setPassword('Admin123*') }}>
                <span className="role-badge superadmin">Superadmin</span>
                <span>admin@turnix.demo</span>
              </div>
              <div className="demo-row" onClick={() => { setEmail('negocio@turnix.demo'); setPassword('Negocio123*') }}>
                <span className="role-badge tenant">Negocio</span>
                <span>negocio@turnix.demo</span>
              </div>
              <div className="demo-row" onClick={() => { setEmail('staff@turnix.demo'); setPassword('Staff123*') }}>
                <span className="role-badge staff">Personal</span>
                <span>staff@turnix.demo</span>
              </div>
            </div>
            <p className="demo-note">Haz clic en un usuario para autocompletar</p>
          </div>
        </div>
      </div>
    </div>
  )
}
