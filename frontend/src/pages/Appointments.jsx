import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const STATUS_LABELS = { pending: 'Pendiente', confirmed: 'Confirmada', cancelled: 'Cancelada', completed: 'Completada' }

export default function Appointments() {
  const { user, isSuperadmin, isStaff } = useAuth()
  const [appointments,  setAppointments]  = useState([])
  const [services,      setServices]      = useState([])
  const [clients,       setClients]       = useState([])
  const [businesses,    setBusinesses]    = useState([])
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState(null)
  const [modal,         setModal]         = useState(false)
  const [form,          setForm]          = useState({})
  const [saving,        setSaving]        = useState(false)
  const [feedback,      setFeedback]      = useState(null)
  const [filterDate,    setFilterDate]    = useState('')
  const [filterStatus,  setFilterStatus]  = useState('')
  const [filterTenant,  setFilterTenant]  = useState('')

  const emptyForm = () => ({
    tenant_id:        isSuperadmin ? '' : (user?.tenant_id || ''),
    service_id:       '',
    client_id:        '',
    appointment_date: '',
    start_time:       '',
    notes:            '',
  })

  const load = () => {
    setLoading(true)
    const params = {}
    if (filterDate)   params.date      = filterDate
    if (filterStatus) params.status    = filterStatus
    if (isSuperadmin && filterTenant) params.tenant_id = filterTenant

    const calls = [api.getAppointments(params), api.getServices(), api.getClients()]
    if (isSuperadmin) calls.push(api.getBusinesses())

    Promise.all(calls)
      .then(([a, s, c, b]) => {
        setAppointments(a || [])
        setServices(s || [])
        setClients(c || [])
        if (b) setBusinesses(b)
        setLoading(false)
      })
      .catch(e => {
        setError(e.message || 'No fue posible cargar las citas.')
        setLoading(false)
      })
  }

  useEffect(load, [filterDate, filterStatus, filterTenant])

  const clientName   = id => clients.find(c => c.id === id)?.full_name || `#${id}`
  const serviceName  = id => services.find(s => s.id === id)?.name     || `#${id}`
  const businessName = id => businesses.find(b => b.id === id)?.name   || `#${id}`

  const openCreate = () => { setForm(emptyForm()); setModal(true); setFeedback(null) }
  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const [h, m] = form.start_time.split(':')
      await api.createAppointment({
        ...form,
        tenant_id:  parseInt(form.tenant_id),
        service_id: parseInt(form.service_id),
        client_id:  parseInt(form.client_id),
        start_time: `${h}:${m}:00`,
      })
      setModal(false)
      load()
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const handleCancel = async id => {
    try { await api.cancelAppointment(id); load() } catch (e) { setFeedback({ type: 'error', msg: e.message }) }
  }
  const handleComplete = async id => {
    try { await api.completeAppointment(id); load() } catch (e) { setFeedback({ type: 'error', msg: e.message }) }
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  // Filtrar servicios según el negocio seleccionado en el formulario
  const availableServices = services.filter(s =>
    s.is_active && (!form.tenant_id || s.tenant_id === parseInt(form.tenant_id))
  )
  // Filtrar clientes según el negocio seleccionado en el formulario
  const availableClients = clients.filter(c =>
    !form.tenant_id || c.tenant_id === parseInt(form.tenant_id)
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Citas</h1>
          <p>
            {isSuperadmin
              ? 'Todas las citas de la plataforma'
              : `Citas de ${user?.tenant_name || 'tu negocio'}`}
          </p>
        </div>
        {!isStaff && <button className="btn btn-primary" onClick={openCreate}>+ Nueva cita</button>}
      </div>

      {/* Filtros */}
      <div className="page-toolbar">
        <div className="filter-group">
          <input
            type="date"
            value={filterDate}
            onChange={e => setFilterDate(e.target.value)}
            className="filter-select"
          />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="filter-select"
          >
            <option value="">Todos los estados</option>
            <option value="pending">Pendiente</option>
            <option value="confirmed">Confirmada</option>
            <option value="cancelled">Cancelada</option>
            <option value="completed">Completada</option>
          </select>
          {isSuperadmin && (
            <select
              value={filterTenant}
              onChange={e => setFilterTenant(e.target.value)}
              className="filter-select"
            >
              <option value="">Todos los negocios</option>
              {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          )}
        </div>
        {(filterDate || filterStatus || filterTenant) && (
          <div className="action-group">
            <button type="button" className="btn btn-outline" onClick={() => { setFilterDate(''); setFilterStatus(''); setFilterTenant('') }}>
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      <div className="table-card">
        {appointments.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state-title">Sin citas para mostrar</h2>
            <p className="empty-state-text">No hay citas{filterDate || filterStatus || filterTenant ? ' con los filtros aplicados.' : ' registradas.'}</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table appointments-table">
            <thead>
              <tr>
                {isSuperadmin && <th>Negocio</th>}
                <th>Fecha</th>
                <th>Hora</th>
                <th>Cliente</th>
                <th>Servicio</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map(a => (
                <tr key={a.id}>
                  {isSuperadmin && <td><span className="cell-main">{businessName(a.tenant_id)}</span></td>}
                  <td className="cell-nowrap">{a.appointment_date}</td>
                  <td className="cell-nowrap">{a.start_time?.slice(0, 5)}</td>
                  <td><span className="cell-main">{clientName(a.client_id)}</span></td>
                  <td className="cell-nowrap">{serviceName(a.service_id)}</td>
                  <td>
                    <span className={`badge badge-${a.status}`}>
                      {STATUS_LABELS[a.status] || a.status}
                    </span>
                  </td>
                  <td className="cell-actions">
                    <div className="table-actions">
                      {!isStaff && ['pending', 'confirmed'].includes(a.status) && (
                        <button className="btn btn-success btn-sm" onClick={() => handleComplete(a.id)}>
                          Completar
                        </button>
                      )}
                      {!isStaff && !['cancelled', 'completed'].includes(a.status) && (
                        <button className="btn btn-danger btn-sm" onClick={() => handleCancel(a.id)}>
                          Cancelar
                        </button>
                      )}
                      {isStaff && a.status === 'confirmed' && (
                        <button className="btn btn-success btn-sm" onClick={() => handleComplete(a.id)}>
                          Completar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {/* Modal nueva cita */}
      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>Nueva cita</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && (
              <div className={`alert alert-${feedback.type} modal-alert`}>
                {feedback.msg}
              </div>
            )}
            <form onSubmit={handleSubmit} className="modal-form" noValidate>
              {isSuperadmin && (
                <div className="form-group">
                  <label>Negocio *</label>
                  <select className="form-select" name="tenant_id" value={form.tenant_id} onChange={handleChange}>
                    <option value="">Selecciona un negocio</option>
                    {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>Servicio *</label>
                <select className="form-select" name="service_id" value={form.service_id} onChange={handleChange}>
                  <option value="">Selecciona un servicio</option>
                  {availableServices.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.duration_minutes} min — ${Number(s.price).toLocaleString('es-CO')})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Cliente *</label>
                <select className="form-select" name="client_id" value={form.client_id} onChange={handleChange}>
                  <option value="">Selecciona un cliente</option>
                  {availableClients.map(c => <option key={c.id} value={c.id}>{c.full_name}</option>)}
                </select>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Fecha *</label>
                  <input className="form-input" type="date" name="appointment_date" value={form.appointment_date} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>Hora inicio *</label>
                  <input className="form-input" type="time" name="start_time" value={form.start_time} onChange={handleChange} />
                </div>
              </div>
              <div className="form-group">
                <label>Notas</label>
                <textarea className="form-textarea" name="notes" value={form.notes} onChange={handleChange} rows={2} placeholder="Observaciones de la cita..." />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando…' : 'Crear cita'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
