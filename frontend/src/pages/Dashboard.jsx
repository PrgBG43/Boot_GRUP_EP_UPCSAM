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
    pending:   { label: 'Pendiente',  cls: 'badge-warning' },
    confirmed: { label: 'Confirmada', cls: 'badge-success' },
    cancelled: { label: 'Cancelada',  cls: 'badge-danger' },
    completed: { label: 'Completada', cls: 'badge-neutral' },
  }
  const s = map[status] || { label: status, cls: '' }
  return <span className={`badge ${s.cls}`}>{s.label}</span>
}

// ── Dashboard Superadmin ───────────────────────────────────
function SuperadminDashboard() {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = () => {
    api.getSuperadminDashboard()
      .then(d => { setData(d); setLastUpdated(new Date()) })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
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
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Negocios totales"    value={data.total_tenants}          color="#6c3fc5" icon="NG" />
        <StatCard label="Negocios activos"    value={data.active_tenants}         color="#22c55e" icon="AC" />
        <StatCard label="Negocios premium"    value={data.premium_tenants}        color="#8b5cf6" icon="PR" />
        <StatCard label="Negocios gratuitos"  value={data.free_tenants}           color="#10b981" icon="GR" />
        <StatCard label="Clientes totales"    value={data.total_clients}          color="#3b82f6" icon="CL" />
        <StatCard label="Citas este mes"      value={data.appointments_this_month} color="#f59e0b" icon="CM" />
        <StatCard label="Negocios archivados" value={data.archived_tenants}       color="#64748b" icon="AR" />
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

        <div className="card">
          <h2 className="card-title">Uso del plan Gratuito</h2>
          {(data.tenants_near_limit?.length || data.tenants_limit_reached?.length) ? (
            <div className="top-list">
              {[...(data.tenants_limit_reached || []), ...(data.tenants_near_limit || [])].slice(0, 8).map(item => (
                <div key={item.tenant_id} className="top-list-item">
                  <span className="top-name">{item.tenant_name}</span>
                  <span className={`badge ${item.limit_reached ? 'badge-danger' : 'badge-warning'}`}>
                    {item.used_this_month}/{item.monthly_limit}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state-sm">Sin negocios cercanos al limite</div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Dashboard Tenant Admin / Staff ────────────────────────
function TenantDashboard() {
  const { user, isSuperadmin, activeTenantId } = useAuth()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = () => {
    if (isSuperadmin && !activeTenantId) {
      setLoading(false)
      setData(null)
      return
    }
    setLoading(true)
    api.getTenantDashboard(isSuperadmin ? activeTenantId : null)
      .then(d => { setData(d); setLastUpdated(new Date()) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [activeTenantId])

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>
  if (!data)   return (
    <div className="empty-state">
      <h2 className="empty-state-title">Selecciona un negocio</h2>
      <p className="empty-state-text">Selecciona un negocio en el menú lateral para ver su dashboard.</p>
    </div>
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>{user?.tenant_name || 'Resumen del negocio'}</p>
        </div>
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Citas hoy"            value={data.appointments_today}  color="#6c3fc5" icon="CH" />
        <StatCard label="Citas esta semana"    value={data.appointments_week}   color="#3b82f6" icon="CS" />
        <StatCard label="Citas este mes"       value={data.appointments_month}  color="#f59e0b" icon="CM" />
        <StatCard label="Pendientes"           value={data.pending_month}       color="#0ea5e9" icon="PE" />
        <StatCard label="Completadas"          value={data.completed_month}     color="#22c55e" icon="CO" />
        <StatCard label="Conversaciones"       value={data.conversations_month} color="#8b5cf6" icon="CV" />
        <StatCard label="Clientes registrados" value={data.total_clients}       color="#22c55e" icon="CL" />
        <StatCard label="Servicios activos"    value={data.active_services}     color="#ec4899" icon="SV"
          sub={data.total_services > data.active_services ? `${data.total_services - data.active_services} inactivos` : null} />
        <StatCard label="Cancelaciones (%)"    value={`${data.cancellation_rate}%`} color="#ef4444" icon="CA" />
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

        {/* Plan y limites */}
        {data.plan_usage && (
          <div className="card">
            <h2 className="card-title">Uso del plan</h2>
            <div className="inline-meta">
              <span className="badge badge-plan">{data.plan_usage.plan}</span>
              {data.plan_usage.limit_reached && <span className="badge badge-danger">Limite alcanzado</span>}
              {!data.plan_usage.limit_reached && data.plan_usage.usage_percentage >= 80 && <span className="badge badge-warning">Uso alto</span>}
            </div>
            <PlanBar
              label="Citas del mes"
              used={data.plan_usage.used_this_month}
              max={data.plan_usage.monthly_limit}
            />
            {data.plan_usage.monthly_limit ? (
              <p className="card-note">
                Has usado {data.plan_usage.used_this_month} de {data.plan_usage.monthly_limit} citas disponibles este mes.
              </p>
            ) : (
              <p className="card-note">Tu plan Premium tiene citas mensuales ilimitadas.</p>
            )}
          </div>
        )}

        {/* Servicio más solicitado */}
        {data.top_service && (
          <div className="card">
            <h2 className="card-title">Servicio del mes</h2>
            <div className="top-service">
              <span className="top-service-icon">SV</span>
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
            <div className="table-responsive">
              <table className="data-table dashboard-table">
                <thead>
                  <tr><th>Fecha</th><th>Hora</th><th>Estado</th></tr>
                </thead>
                <tbody>
                  {data.upcoming_appointments.map(a => (
                    <tr key={a.id}>
                      <td className="cell-nowrap">{new Date(a.date).toLocaleDateString('es')}</td>
                      <td className="cell-nowrap">{a.start_time.slice(0, 5)}</td>
                      <td><StatusBadge status={a.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { isSuperadmin, activeTenantId } = useAuth()
  // Superadmin sin tenant activo → Panel de plataforma global
  // Superadmin con tenant activo → Dashboard del tenant seleccionado
  if (isSuperadmin && !activeTenantId) return <SuperadminDashboard />
  if (isSuperadmin && activeTenantId)  return <TenantDashboard />
  return <TenantDashboard />
}
