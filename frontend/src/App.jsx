import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Services from './pages/Services.jsx'
import Clients from './pages/Clients.jsx'
import Appointments from './pages/Appointments.jsx'
import Conversations from './pages/Conversations.jsx'
import BusinessConfig from './pages/BusinessConfig.jsx'
import './App.css'

const navItems = [
  { to: '/',              label: '🏠 Dashboard',       end: true },
  { to: '/services',      label: '✂️ Servicios' },
  { to: '/clients',       label: '👥 Clientes' },
  { to: '/appointments',  label: '📅 Citas' },
  { to: '/conversations', label: '💬 Conversaciones' },
  { to: '/business',      label: '⚙️ Negocio' },
]

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">✂️</span>
          <span className="brand-name">Turnix</span>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <p>Panel Administrativo</p>
          <p className="version">v1.0.0</p>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/"              element={<Dashboard />} />
          <Route path="/services"      element={<Services />} />
          <Route path="/clients"       element={<Clients />} />
          <Route path="/appointments"  element={<Appointments />} />
          <Route path="/conversations" element={<Conversations />} />
          <Route path="/business"      element={<BusinessConfig />} />
        </Routes>
      </main>
    </div>
  )
}
