import { useEffect, useState } from 'react'
import api from '../api.js'
import './Dashboard.css'

function StatCard({ icon, label, value, color }) {
  return (
    <div className="stat-card" style={{ borderTop: `4px solid ${color}` }}>
      <div className="stat-icon" style={{ background: color + '22', color }}>{icon}</div>
      <div>
        <div className="stat-value">{value ?? '—'}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0]

    Promise.all([
      api.getServices(),
      api.getClients(),
      api.getAppointments(),
      api.getAppointments({ date: today }),
    ]).then(([services, clients, appointments, todayAppts]) => {
      setStats({
        activeServices: (services || []).filter(s => s.is_active).length,
        totalClients: (clients || []).length,
        totalAppointments: (appointments || []).length,
        todayAppointments: (todayAppts || []).length,
        recentAppointments: (appointments || []).slice(0, 5),
      })
      setLoading(false)
    }).catch(e => {
      setError(e.message || 'No fue posible cargar el dashboard.')
      setLoading(false)
    })
  }, [])

  if (loading) return <div className="spinner" />
  if (error) return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Resumen general del negocio</p>
      </div>

      <div className="stats-grid">
        <StatCard icon="✂️" label="Servicios activos"    value={stats.activeServices}     color="#6c3fc5" />
        <StatCard icon="👥" label="Clientes registrados" value={stats.totalClients}        color="#3b82f6" />
        <StatCard icon="📋" label="Total de citas"        value={stats.totalAppointments}   color="#f59e0b" />
        <StatCard icon="📅" label="Citas hoy"             value={stats.todayAppointments}   color="#22c55e" />
      </div>

      <div className="card" style={{ marginTop: '2rem' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Últimas citas registradas</h2>
        {stats.recentAppointments.length === 0 ? (
          <div className="empty-state">
            <div className="icon">📅</div>
            <p>No hay citas registradas aún.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Fecha</th>
                <th>Hora</th>
                <th>Cliente</th>
                <th>Servicio</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {stats.recentAppointments.map(a => (
                <tr key={a.id}>
                  <td>#{a.id}</td>
                  <td>{a.appointment_date}</td>
                  <td>{a.start_time}</td>
                  <td>#{a.client_id}</td>
                  <td>#{a.service_id}</td>
                  <td><span className={`badge badge-${a.status}`}>{a.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
