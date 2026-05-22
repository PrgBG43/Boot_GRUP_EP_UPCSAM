import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { FieldError } from '../components/FormMessages.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import './Login.css'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/'

  const [form, setForm] = useState({ email: '', password: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(current => ({ ...current, [name]: value }))
    if (fieldErrors[name]) {
      setFieldErrors(current => ({ ...current, [name]: null }))
    }
    if (error) setError(null)
  }

  const validate = () => {
    const errors = {}
    if (!form.email.trim()) errors.email = 'El correo electrónico es obligatorio.'
    else if (!EMAIL_RE.test(form.email.trim())) errors.email = 'Ingresa un correo electrónico válido.'
    if (!form.password) errors.password = 'La contraseña es obligatoria.'
    return errors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errors = validate()
    if (Object.keys(errors).length) {
      setFieldErrors(errors)
      setError('Corrige los campos marcados para continuar.')
      return
    }

    setError(null)
    setLoading(true)
    try {
      await login(form.email.trim(), form.password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Correo electrónico o contraseña incorrectos.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="login-brand">
          <div className="login-logo">T</div>
          <span className="login-brand-name">Turnix</span>
        </div>
        <h1 className="login-title">Gestión de citas para negocios de belleza</h1>
        <p className="login-subtitle">
          Plataforma SaaS para administrar servicios, clientes, agenda y conversaciones desde un panel profesional.
        </p>
        <div className="login-features">
          <div className="feature-item"><span className="feature-icon">01</span><span>Negocios multi-tenant</span></div>
          <div className="feature-item"><span className="feature-icon">02</span><span>Roles y accesos controlados</span></div>
          <div className="feature-item"><span className="feature-icon">03</span><span>Agendamiento conectado con Telegram</span></div>
        </div>
      </div>

      <div className="login-right">
        <div className="login-card">
          <div className="login-card-header">
            <h2>Iniciar sesión</h2>
            <p>Ingresa tus credenciales para acceder al panel</p>
          </div>

          {error && <div className="login-error">{error}</div>}

          <form onSubmit={handleSubmit} className="login-form" noValidate>
            <div className="form-group">
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="usuario@ejemplo.com"
                autoComplete="email"
                className={fieldErrors.email ? 'input-error' : ''}
              />
              <FieldError msg={fieldErrors.email} />
            </div>
            <div className="form-group">
              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Contraseña"
                autoComplete="current-password"
                className={fieldErrors.password ? 'input-error' : ''}
              />
              <FieldError msg={fieldErrors.password} />
            </div>
            <button type="submit" className="btn btn-primary btn-block login-btn" disabled={loading}>
              {loading ? 'Verificando...' : 'Ingresar al panel'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

