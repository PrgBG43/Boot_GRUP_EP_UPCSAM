import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

export default function Services() {
  const { user, isSuperadmin } = useAuth()
  const [services, setServices]   = useState([])
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [form, setForm]           = useState({})
  const [editing, setEditing]     = useState(null)
  const [saving, setSaving]       = useState(false)
  const [feedback, setFeedback]   = useState(null)

  const emptyForm = () => ({
    tenant_id: isSuperadmin ? '' : user?.tenant_id,
    name: '', description: '', duration_minutes: 30, price: '', is_active: true,
  })

  const load = () => {
    setLoading(true)
    const calls = [api.getServices()]
    if (isSuperadmin) calls.push(api.getBusinesses())
    Promise.all(calls)
      .then(([s, b]) => { setServices(s || []); if (b) setBusinesses(b); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [])

  const openCreate = () => { setForm(emptyForm()); setEditing(null); setModal(true); setFeedback(null) }
  const openEdit   = (s) => {
    setForm({ tenant_id: s.tenant_id, name: s.name, description: s.description || '', duration_minutes: s.duration_minutes, price: s.price, is_active: s.is_active })
    setEditing(s.id); setModal(true); setFeedback(null)
  }

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      const payload = {
        ...form,
        tenant_id: parseInt(form.tenant_id),
        duration_minutes: parseInt(form.duration_minutes),
        price: parseFloat(form.price),
      }
      if (editing) await api.updateService(editing, payload)
      else          await api.createService(payload)
      setModal(false); load()
    } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
    setSaving(false)
  }

  const handleToggle = async (s) => {
    try { await api.updateService(s.id, { is_active: !s.is_active }); load() }
    catch(e) { alert(e.message) }
  }

  const businessName = (id) => businesses.find(b => b.id === id)?.name || `Negocio #${id}`

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Servicios</h1>
          <p>Gestiona los servicios ofrecidos por el negocio</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Nuevo servicio</button>
      </div>

      <div className="card">
        {services.length === 0 ? (
          <div className="empty-state">
            <div className="icon">✂ï¸</div>
            <p>No hay servicios registrados aún.</p>
            <button className="btn btn-primary" onClick={openCreate}>Crear primer servicio</button>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                {isSuperadmin && <th>Negocio</th>}
                <th>Nombre</th>
                <th>Duración</th>
                <th>Precio</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {services.map(s => (
                <tr key={s.id}>
                  {isSuperadmin && <td className="table-sub">{businessName(s.tenant_id)}</td>}
                  <td>
                    <strong>{s.name}</strong>
                    {s.description && <div className="table-sub">{s.description}</div>}
                  </td>
                  <td>{s.duration_minutes} min</td>
                  <td>${Number(s.price).toLocaleString('es-CO')}</td>
                  <td>
                    <span className={`badge ${s.is_active ? 'badge-confirmed' : 'badge-cancelled'}`}>
                      {s.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td>
                    <div className="table-actions">
                      <button className="btn-sm btn-outline-sm" onClick={() => openEdit(s)}>Editar</button>
                      <button
                        className={`btn-sm ${s.is_active ? 'btn-danger-sm' : 'btn-success-sm'}`}
                        onClick={() => handleToggle(s)}
                      >
                        {s.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
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
              <h3>{editing ? 'Editar servicio' : 'Nuevo servicio'}</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type}`} style={{margin:'0 1.5rem'}}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit} className="modal-form">
              {isSuperadmin && (
                <div className="form-group">
                  <label>Negocio *</label>
                  <select name="tenant_id" value={form.tenant_id} onChange={handleChange} required>
                    <option value="">Selecciona un negocio</option>
                    {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>Nombre *</label>
                <input name="name" value={form.name} onChange={handleChange} required placeholder="Ej: Corte de cabello" />
              </div>
              <div className="form-group">
                <label>Descripción</label>
                <textarea name="description" value={form.description} onChange={handleChange} rows={2} placeholder="Descripción breve del servicio" />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Duración (min) *</label>
                  <input type="number" name="duration_minutes" value={form.duration_minutes} onChange={handleChange} min={5} required />
                </div>
                <div className="form-group">
                  <label>Precio (COP) *</label>
                  <input type="number" name="price" value={form.price} onChange={handleChange} step="0.01" min={0} required />
                </div>
              </div>
              <div className="form-group form-check">
                <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} id="svc_active" />
                <label htmlFor="svc_active">Servicio activo</label>
              </div>
            </form>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
              <button type="button" className="btn btn-primary" disabled={saving} onClick={handleSubmit}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
