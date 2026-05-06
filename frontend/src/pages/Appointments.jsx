import { useEffect, useState } from 'react'
import api from '../api.js'

const STATUS_LABELS = { pending: 'Pendiente', confirmed: 'Confirmada', cancelled: 'Cancelada', completed: 'Completada' }

export default function Appointments() {
  const [appointments, setAppointments] = useState([])
  const [services,     setServices]     = useState([])
  const [clients,      setClients]      = useState([])
  const [businesses,   setBusinesses]   = useState([])
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState(null)
  const [modal,        setModal]        = useState(false)
  const [form,         setForm]         = useState({ tenant_id: '', service_id: '', client_id: '', appointment_date: '', start_time: '', notes: '' })
  const [saving,       setSaving]       = useState(false)
  const [feedback,     setFeedback]     = useState(null)
  const [filterDate,   setFilterDate]   = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  const load = () => {
    setLoading(true)
    const params = {}
    if (filterDate)   params.date   = filterDate
    if (filterStatus) params.status = filterStatus
    Promise.all([
      api.getAppointments(params),
      api.getServices(),
      api.getClients(),
      api.getBusinesses(),
    ]).then(([a, s, c, b]) => {
      setAppointments(a || []); setServices(s || []); setClients(c || []); setBusinesses(b || [])
      setLoading(false)
    }).catch(e => {
      setError(e.message || 'No fue posible cargar citas, servicios o clientes.')
      setLoading(false)
    })
  }

  useEffect(load, [filterDate, filterStatus])

  const clientName  = id => clients.find(c => c.id === id)?.full_name  || `#${id}`
  const serviceName = id => services.find(s => s.id === id)?.name       || `#${id}`

  const openCreate = () => { setForm({ tenant_id: '', service_id: '', client_id: '', appointment_date: '', start_time: '', notes: '' }); setModal(true); setFeedback(null) }

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      const [h, m] = form.start_time.split(':')
      await api.createAppointment({
        ...form,
        tenant_id: parseInt(form.tenant_id),
        service_id: parseInt(form.service_id),
        client_id: parseInt(form.client_id),
        start_time: `${h}:${m}:00`,
      })
      setModal(false); load()
    } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
    setSaving(false)
  }

  const handleCancel   = async id => { if (!confirm('¿Cancelar esta cita?'))   return; try { await api.cancelAppointment(id);   load() } catch(e) { alert(e.message) } }
  const handleComplete = async id => { if (!confirm('¿Marcar como completada?')) return; try { await api.completeAppointment(id); load() } catch(e) { alert(e.message) } }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <h1>Citas</h1>
        <p>Gestiona y consulta las citas del negocio</p>
      </div>

      <div className="actions-bar">
        <div className="filters">
          <input type="date" value={filterDate} onChange={e => setFilterDate(e.target.value)} style={{maxWidth:'160px'}} />
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{maxWidth:'160px'}}>
            <option value="">Todos los estados</option>
            <option value="pending">Pendiente</option>
            <option value="confirmed">Confirmada</option>
            <option value="cancelled">Cancelada</option>
            <option value="completed">Completada</option>
          </select>
          {(filterDate || filterStatus) && <button className="btn-ghost btn-sm" onClick={() => { setFilterDate(''); setFilterStatus('') }}>Limpiar filtros</button>}
        </div>
        <button className="btn-primary" onClick={openCreate}>+ Nueva cita</button>
      </div>

      <div className="card">
        {appointments.length === 0 ? (
          <div className="empty-state"><div className="icon">📅</div><p>No hay citas{filterDate || filterStatus ? ' con los filtros aplicados.' : ' registradas.'}</p></div>
        ) : (
          <table>
            <thead><tr><th>ID</th><th>Fecha</th><th>Hora</th><th>Cliente</th><th>Servicio</th><th>Estado</th><th>Acciones</th></tr></thead>
            <tbody>
              {appointments.map(a => (
                <tr key={a.id}>
                  <td>#{a.id}</td>
                  <td>{a.appointment_date}</td>
                  <td>{a.start_time} – {a.end_time}</td>
                  <td>{clientName(a.client_id)}</td>
                  <td>{serviceName(a.service_id)}</td>
                  <td><span className={`badge badge-${a.status}`}>{STATUS_LABELS[a.status] || a.status}</span></td>
                  <td style={{display:'flex',gap:'.3rem',flexWrap:'wrap'}}>
                    {a.status === 'pending' && <button className="btn-success btn-sm" onClick={() => handleComplete(a.id)}>Completar</button>}
                    {!['cancelled','completed'].includes(a.status) && <button className="btn-danger btn-sm" onClick={() => handleCancel(a.id)}>Cancelar</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>Nueva cita</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Negocio *</label>
                <select name="tenant_id" value={form.tenant_id} onChange={handleChange} required>
                  <option value="">Selecciona un negocio</option>
                  {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Servicio *</label>
                <select name="service_id" value={form.service_id} onChange={handleChange} required>
                  <option value="">Selecciona un servicio</option>
                  {services.filter(s => s.is_active && (!form.tenant_id || s.tenant_id === parseInt(form.tenant_id))).map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.duration_minutes} min)</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Cliente *</label>
                <select name="client_id" value={form.client_id} onChange={handleChange} required>
                  <option value="">Selecciona un cliente</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                </select>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1rem'}}>
                <div className="form-group"><label>Fecha *</label><input type="date" name="appointment_date" value={form.appointment_date} onChange={handleChange} required /></div>
                <div className="form-group"><label>Hora inicio *</label><input type="time" name="start_time" value={form.start_time} onChange={handleChange} required /></div>
              </div>
              <div className="form-group"><label>Notas</label><textarea name="notes" value={form.notes} onChange={handleChange} rows={2} /></div>
              <div style={{display:'flex',gap:'.6rem',justifyContent:'flex-end',marginTop:'1rem'}}>
                <button type="button" className="btn-ghost" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Crear cita'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
