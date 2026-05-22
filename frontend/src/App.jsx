import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import api from './api.js'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { useAuth } from './context/AuthContext.jsx'
import Appointments from './pages/Appointments.jsx'
import BusinessConfig from './pages/BusinessConfig.jsx'
import Clients from './pages/Clients.jsx'
import Conversations from './pages/Conversations.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Login from './pages/Login.jsx'
import Services from './pages/Services.jsx'
import Staff from './pages/Staff.jsx'
import TelegramConfig from './pages/TelegramConfig.jsx'
import Unauthorized from './pages/Unauthorized.jsx'
import AdminTenants from './pages/admin/Tenants.jsx'
import AdminUsers from './pages/admin/Users.jsx'
import { roleBadgeClass, roleLabel } from './utils/labels.js'
import './App.css'

const SUPERADMIN_NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/admin/tenants', label: 'Negocios' },
  { to: '/admin/users', label: 'Usuarios' },
  { to: '/appointments', label: 'Citas' },
  { to: '/clients', label: 'Clientes' },
  { to: '/services', label: 'Servicios' },
  { to: '/conversations', label: 'Conversaciones' },
  { to: '/staff', label: 'Personal' },
  { to: '/telegram', label: 'Telegram' },
]

const TENANT_ADMIN_NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/business', label: 'Mi negocio' },
  { to: '/services', label: 'Servicios' },
  { to: '/appointments', label: 'Citas' },
  { to: '/clients', label: 'Clientes' },
  { to: '/staff', label: 'Personal' },
  { to: '/telegram', label: 'Telegram' },
  { to: '/conversations', label: 'Conversaciones' },
]

const STAFF_NAV = [
  { to: '/', label: 'Mi agenda', end: true },
  { to: '/appointments', label: 'Citas' },
  { to: '/clients', label: 'Clientes' },
]

function RoleBadge({ role }) {
  return <span className={`badge badge-role ${roleBadgeClass(role)}`}>{roleLabel(role)}</span>
}

function TenantSelector() {
  const { activeTenant, setActiveTenant } = useAuth()
  const [tenants, setTenants] = useState([])

  useEffect(() => {
    api.getBusinesses({ page_size: 100 }).then(data => setTenants(data?.items || data || [])).catch(() => {})
  }, [])

  const handleChange = (e) => {
    const id = parseInt(e.target.value)
    if (!id) {
      setActiveTenant(null)
      return
    }
    const tenant = tenants.find(item => item.id === id)
    if (tenant) setActiveTenant({ id: tenant.id, name: tenant.name })
  }

  return (
    <div className="tenant-selector">
      <label className="tenant-selector-label">Negocio activo</label>
      <select className="tenant-selector-select" value={activeTenant?.id || ''} onChange={handleChange}>
        <option value="">Vista global</option>
        {tenants.map(tenant => (
          <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
        ))}
      </select>
    </div>
  )
}

function Layout({ navItems }) {
  const { user, isSuperadmin, activeTenantName, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo">T</div>
          <span className="brand-name">Turnix</span>
        </div>

        {isSuperadmin && <TenantSelector />}

        {!isSuperadmin && user?.tenant_name && (
          <div className="sidebar-tenant">
            <span className="tenant-label">Negocio activo</span>
            <span className="tenant-name">{user.tenant_name}</span>
          </div>
        )}
        {isSuperadmin && !activeTenantName && (
          <div className="sidebar-tenant">
            <span className="tenant-label">Vista global</span>
            <span className="tenant-name">Plataforma Turnix</span>
          </div>
        )}

        <nav className="sidebar-nav">
          {navItems.map(({ to, end, label }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{user?.email?.[0]?.toUpperCase()}</div>
            <div className="user-details">
              <span className="user-email">{user?.email}</span>
              <RoleBadge role={user?.role} />
            </div>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Cerrar sesión">
            Salir
          </button>
        </div>
      </aside>

      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-left">
            {activeTenantName && <span className="topbar-tenant">{activeTenantName}</span>}
            {isSuperadmin && !activeTenantName && (
              <span className="topbar-tenant topbar-tenant-global">Vista global - Plataforma Turnix</span>
            )}
          </div>
          <div className="topbar-right">
            <RoleBadge role={user?.role} />
            <span className="topbar-email">{user?.email}</span>
          </div>
        </header>
        <main className="main-content-wrapper">
          <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/services" element={
              <ProtectedRoute roles={['superadmin', 'tenant_admin']}>
                <Services />
              </ProtectedRoute>
            } />
            <Route path="/clients" element={<Clients />} />
            <Route path="/appointments" element={<Appointments />} />
            <Route path="/conversations" element={
              <ProtectedRoute roles={['superadmin', 'tenant_admin']}>
                <Conversations />
              </ProtectedRoute>
            } />
            <Route path="/business" element={
              <ProtectedRoute roles={['tenant_admin']}>
                <BusinessConfig />
              </ProtectedRoute>
            } />
            <Route path="/staff" element={
              <ProtectedRoute roles={['superadmin', 'tenant_admin']}>
                <Staff />
              </ProtectedRoute>
            } />
            <Route path="/telegram" element={
              <ProtectedRoute roles={['superadmin', 'tenant_admin']}>
                <TelegramConfig />
              </ProtectedRoute>
            } />
            <Route path="/admin/tenants" element={
              <ProtectedRoute roles={['superadmin']}>
                <AdminTenants />
              </ProtectedRoute>
            } />
            <Route path="/admin/users" element={
              <ProtectedRoute roles={['superadmin']}>
                <AdminUsers />
              </ProtectedRoute>
            } />
            <Route path="/unauthorized" element={<Unauthorized />} />
          </Routes>
          </div>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const { isAuthenticated, isSuperadmin, isStaff } = useAuth()
  const navItems = isSuperadmin ? SUPERADMIN_NAV : isStaff ? STAFF_NAV : TENANT_ADMIN_NAV

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={
        <ProtectedRoute>
          <Layout navItems={navItems} />
        </ProtectedRoute>
      } />
    </Routes>
  )
}
