import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Services from './pages/Services.jsx'
import Clients from './pages/Clients.jsx'
import Appointments from './pages/Appointments.jsx'
import Conversations from './pages/Conversations.jsx'
import BusinessConfig from './pages/BusinessConfig.jsx'
import Staff from './pages/Staff.jsx'
import TelegramConfig from './pages/TelegramConfig.jsx'
import Unauthorized from './pages/Unauthorized.jsx'
import AdminTenants from './pages/admin/Tenants.jsx'
import './App.css'

const SUPERADMIN_NAV = [
  { to: '/',               label: 'Dashboard',     icon: '⬛', end: true },
  { to: '/admin/tenants',  label: 'Negocios',       icon: '🏢' },
  { to: '/appointments',   label: 'Citas',          icon: '📅' },
  { to: '/clients',        label: 'Clientes',       icon: '👥' },
]

const TENANT_ADMIN_NAV = [
  { to: '/',               label: 'Dashboard',     icon: '⬛', end: true },
  { to: '/services',       label: 'Servicios',      icon: '✂️' },
  { to: '/appointments',   label: 'Citas',          icon: '📅' },
  { to: '/clients',        label: 'Clientes',       icon: '👥' },
  { to: '/staff',          label: 'Personal',       icon: '👤' },
  { to: '/conversations',  label: 'Conversaciones', icon: '💬' },
  { to: '/telegram',       label: 'Telegram',       icon: '🤖' },
  { to: '/business',       label: 'Mi Negocio',     icon: '⚙️' },
]

const STAFF_NAV = [
  { to: '/',               label: 'Mi Agenda',     icon: '📅', end: true },
  { to: '/appointments',   label: 'Citas',          icon: '📋' },
  { to: '/clients',        label: 'Clientes',       icon: '👥' },
]

function RoleBadge({ role }) {
  const labels = {
    superadmin:   { label: 'Superadmin', cls: 'role-superadmin' },
    tenant_admin: { label: 'Administrador', cls: 'role-admin' },
    staff:        { label: 'Personal', cls: 'role-staff' },
    customer:     { label: 'Cliente', cls: 'role-customer' },
  }
  const r = labels[role] || { label: role, cls: '' }
  return <span className={`role-pill ${r.cls}`}>{r.label}</span>
}

function Layout({ navItems }) {
  const { user, logout } = useAuth()
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

        {user?.tenant_name && (
          <div className="sidebar-tenant">
            <span className="tenant-label">Negocio activo</span>
            <span className="tenant-name">{user.tenant_name}</span>
          </div>
        )}

        <nav className="sidebar-nav">
          {navItems.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{icon}</span>
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
            ⏻
          </button>
        </div>
      </aside>

      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-left">
            {user?.tenant_name && <span className="topbar-tenant">{user.tenant_name}</span>}
          </div>
          <div className="topbar-right">
            <RoleBadge role={user?.role} />
            <span className="topbar-email">{user?.email}</span>
          </div>
        </header>
        <main className="main-content">
          <Routes>
            <Route path="/"               element={<Dashboard />} />
            <Route path="/services"       element={<Services />} />
            <Route path="/clients"        element={<Clients />} />
            <Route path="/appointments"   element={<Appointments />} />
            <Route path="/conversations"  element={<Conversations />} />
            <Route path="/business"       element={<BusinessConfig />} />
            <Route path="/staff"          element={
              <ProtectedRoute roles={['superadmin','tenant_admin']}>
                <Staff />
              </ProtectedRoute>
            } />
            <Route path="/telegram"       element={
              <ProtectedRoute roles={['superadmin','tenant_admin']}>
                <TelegramConfig />
              </ProtectedRoute>
            } />
            <Route path="/admin/tenants"  element={
              <ProtectedRoute roles={['superadmin']}>
                <AdminTenants />
              </ProtectedRoute>
            } />
            <Route path="/unauthorized"   element={<Unauthorized />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const { isAuthenticated, isSuperadmin, isStaff } = useAuth()

  const navItems = isSuperadmin ? SUPERADMIN_NAV
                 : isStaff     ? STAFF_NAV
                 :               TENANT_ADMIN_NAV

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
