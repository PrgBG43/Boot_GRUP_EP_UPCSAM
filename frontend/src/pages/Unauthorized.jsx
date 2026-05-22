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
    <div className="unauthorized-page">
      <div className="unauthorized-card">
        <h1>Acceso no permitido</h1>
        <p>
          No tienes permisos para acceder a esta sección. Si crees que esto es un error, contacta al administrador del sistema.
        </p>
        <button
          onClick={goHome}
          className="btn btn-primary"
        >
          Volver al inicio
        </button>
      </div>
    </div>
  )
}

