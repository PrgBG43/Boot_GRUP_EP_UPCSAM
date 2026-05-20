import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Unauthorized() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const goHome = () => {
    if (user?.role) navigate('/')
    else navigate('/login')
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-page, #f8fafc)',
      padding: '2rem',
    }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '3rem',
        maxWidth: '440px',
        width: '100%',
        textAlign: 'center',
        boxShadow: '0 8px 32px rgba(0,0,0,.08)',
        border: '1px solid #e9ecef',
      }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary,#1a202c)', marginBottom: '.5rem' }}>
          Acceso no permitido
        </h1>
        <p style={{ color: 'var(--text-muted,#6c757d)', marginBottom: '2rem', lineHeight: 1.6 }}>
          No tienes permisos para acceder a esta sección. Si crees que esto es un error, contacta al administrador del sistema.
        </p>
        <button
          onClick={goHome}
          style={{
            background: 'var(--primary,#5a67d8)',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            padding: '.75rem 2rem',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Volver al inicio
        </button>
      </div>
    </div>
  )
}
