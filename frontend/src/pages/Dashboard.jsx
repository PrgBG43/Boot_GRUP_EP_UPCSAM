import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'
import './Dashboard.css'

function StatCard({ label, value, sub, color, icon }) {
  return (
    <div className="stat-card" style={{ borderTop: `3px solid ${color}` }}>
      <div className="stat-icon" style={{ background: color + '18', color }}>{icon}</div>
      <div className="stat-body">
        <div className="stat-value">{value ?? '—'}</div>
        <div className="stat-label">{label}</div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  )
}

function PlanBar({ used, max, label }) {
  const pct = max ? Math.min(100, Math.round(used / max * 100)) : 0
  const color = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#22c55e'
  return (
    <div className="plan-bar-item">
      <div className="plan-bar-header">
        <span>{label}</span>
        <span>{max ? `${used} / ${max}` : `${used} (ilimitado)`}</span>
      </div>
      {max && (
        <div className="plan-bar-track">
          <div className="plan-bar-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    pending:   { label: 'Pendiente',  cls: 'badge-pending' },
    confirmed: { label: 'Confirmada', cls: 'badge-confirmed' },
    cancelled: { label: 'Cancelada',  cls: 'badge-cancelled' },
    completed: { label: 'Completada', cls: 'badge-completed' },
  }
  const s = map[status] || { label: status, cls: '' }
  return <span className={`badge ${s.cls}`}>{s.label}</span>
}

// ── Dashboard Superadmin ───────────────────────────────────
function SuperadminDashboard() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSuperadminDashboard()
      .then(setData)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="spinner" />
  if (!data)   return <div className="alert alert-error">No se pudo cargar el dashboard</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Panel de Plataforma</h1>
          <p>Vista global de todos los negocios en Turnix</p>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Negocios totales"    value={data.total_tenants}          color="#6c3fc5" icon="🏢" />
        <StatCard label="Negocios activos"    value={data.active_tenants}         color="#22c55e" icon="✅" />
        <StatCard label="Clientes totales"    value={data.total_clients}          color="#3b82f6" icon="👥" />
        <StatCard label="Citas este mes"      value={data.appointments_this_month} color="#f59e0b" icon="📅" />
        <StatCard label="Citas hoy"           value={data.appointments_today}     color="#ec4899" icon="🗓️" />
        <StatCard label="Negocios inactivos"  value={data.inactive_tenants}       color="#ef4444" icon="⛔" />
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <h2 className="card-title">Distribución por plan</h2>
          {data.plan_distribution.length === 0 ? (
            <div className="empty-state-sm">Sin datos</div>
          ) : (
            <div className="plan-dist">
              {data.plan_distribution.map(p => (
                <div key={p.plan} className="plan-dist-item">
                  <span className="plan-dist-label">{p.plan || 'Sin plan'}</span>
                  <span className="plan-dist-count">{p.count} negocios</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="card-title">Top negocios del mes</h2>
          {data.top_tenants_month.length === 0 ? (
            <div className="empty-state-sm">Sin actividad este mes</div>
          ) : (
            <div className="top-list">
              {data.top_tenants_month.map((t, i) => (
                <div key={i} className="top-list-item">
                  <span className="top-rank">#{i + 1}</span>
                  <span className="top-name">{t.name}</span>
                  <span className="top-count">{t.appointments} citas</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Dashboard Tenant Admin / Staff ────────────────────────
function TenantDashboard() {
  const { user } = useAuth()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    api.getTenantDashboard()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>
  if (!data)   return null

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>{user?.tenant_name || 'Resumen del negocio'}</p>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Citas hoy"            value={data.appointments_today}  color="#6c3fc5" icon="🗓️" />
        <StatCard label="Citas esta semana"    value={data.appointments_week}   color="#3b82f6" icon="📅" />
        <StatCard label="Citas este mes"       value={data.appointments_month}  color="#f59e0b" icon="📋" />
        <StatCard label="Clientes registrados" value={data.total_clients}       color="#22c55e" icon="👥" />
        <StatCard label="Servicios activos"    value={data.active_services}     color="#ec4899" icon="✂️"
          sub={data.total_services > data.active_services ? `${data.total_services - data.active_services} inactivos` : null} />
        <StatCard label="Cancelaciones (%)"    value={`${data.cancellation_rate}%`} color="#ef4444" icon="❌" />
      </div>

      <div className="dashboard-grid">
        {/* Gráfica de los últimos 7 días */}
        <div className="card card-wide">
          <h2 className="card-title">Citas — últimos 7 días</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.daily_chart} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }}
                tickFormatter={d => new Date(d).toLocaleDateString('es', { weekday: 'short', day: 'numeric' })} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                formatter={(v) => [v, 'Citas']}
                labelFormatter={(l) => new Date(l).toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'short' })}
              />
              <Bar dataKey="count" fill="#6c3fc5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Plan y límites */}
        {data.plan && (
          <div className="card">
            <h2 className="card-title">Plan activo — {data.plan.display_name}</h2>
            <PlanBar
              label="Citas del mes"
              used={data.plan.appointments_used_month}
              max={data.plan.max_appointments_monthly}
            />
            <PlanBar
              label="Servicios activos"
              used={data.plan.services_used}
              max={data.plan.max_active_services}
            />
          </div>
        )}

        {/* Servicio más solicitado */}
        {data.top_service && (
          <div className="card">
            <h2 className="card-title">Servicio del mes</h2>
            <div className="top-service">
              <span className="top-service-icon">✂️</span>
              <div>
                <div className="top-service-name">{data.top_service.name}</div>
                <div className="top-service-count">{data.top_service.count} citas este mes</div>
              </div>
            </div>
          </div>
        )}

        {/* Próximas citas */}
        <div className="card">
          <h2 className="card-title">Próximas citas</h2>
          {data.upcoming_appointments.length === 0 ? (
            <div className="empty-state-sm">No hay citas próximas programadas.</div>
          ) : (
            <table className="table-sm">
              <thead>
                <tr><th>Fecha</th><th>Hora</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {data.upcoming_appointments.map(a => (
                  <tr key={a.id}>
                    <td>{new Date(a.date).toLocaleDateString('es')}</td>
                    <td>{a.start_time.slice(0, 5)}</td>
                    <td><StatusBadge status={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { isSuperadmin } = useAuth()
  return isSuperadmin ? <SuperadminDashboard /> : <TenantDashboard />
}
