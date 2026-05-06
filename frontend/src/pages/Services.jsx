import { useEffect, useState } from 'react'
import api from '../api.js'

const EMPTY_FORM = { tenant_id: '', name: '', description: '', duration_minutes: 30, price: '', is_active: true }

export default function Services() {
  const [services, setServices]   = useState([])
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [form, setForm]           = useState(EMPTY_FORM)
  const [editing, setEditing]     = useState(null)
  const [saving, setSaving]       = useState(false)
  const [feedback, setFeedback]   = useState(null)

  const load = () => {
    setLoading(true)
    Promise.all([api.getServices(), api.getBusinesses()])
      .then(([s, b]) => { setServices(s || []); setBusinesses(b || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [])

  const openCreate = () => { setForm(EMPTY_FORM); setEditing(null); setModal(true); setFeedback(null) }
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
      const payload = { ...form, tenant_id: parseInt(form.tenant_id), duration_minutes: parseInt(form.duration_minutes), price: parseFloat(form.price) }
      if (editing) await api.updateService(editing, payload)
      else          await api.createService(payload)
      setModal(false); load()
    } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!confirm('¿Desactivar este servicio?')) return
    try { await api.updateService(id, { is_active: false }); load() }
    catch(e) { alert(e.message) }
  }

  const businessName = (id) => businesses.find(b => b.id === id)?.name || `#${id}`

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <h1>Servicios</h1>
        <p>Gestiona los servicios ofrecidos por el negocio</p>
      </div>

      <div className="actions-bar">
        <div />
        <button className="btn-primary" onClick={openCreate}>+ Nuevo servicio</button>
      </div>

      <div className="card">
        {services.length === 0 ? (
          <div className="empty-state"><div className="icon">✂️</div><p>No hay servicios registrados.</p></div>
        ) : (
          <table>
            <thead><tr><th>ID</th><th>Nombre</th><th>Negocio</th><th>Duración</th><th>Precio</th><th>Estado</th><th>Acciones</th></tr></thead>
            <tbody>
              {services.map(s => (
                <tr key={s.id}>
                  <td>#{s.id}</td>
                  <td><strong>{s.name}</strong>{s.description && <div style={{fontSize:'.8rem',color:'var(--text-muted)'}}>{s.description}</div>}</td>
                  <td>{businessName(s.tenant_id)}</td>
                  <td>{s.duration_minutes} min</td>
                  <td>${Number(s.price).toLocaleString('es-CO')}</td>
                  <td><span className={`badge badge-${s.is_active ? 'active' : 'inactive'}`}>{s.is_active ? 'Activo' : 'Inactivo'}</span></td>
                  <td style={{display:'flex',gap:'.4rem'}}>
                    <button className="btn-ghost btn-sm" onClick={() => openEdit(s)}>Editar</button>
                    {s.is_active && <button className="btn-danger btn-sm" onClick={() => handleDelete(s.id)}>Desactivar</button>}
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
            {feedback && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Negocio *</label>
                <select name="tenant_id" value={form.tenant_id} onChange={handleChange} required>
                  <option value="">Selecciona un negocio</option>
                  {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </div>
              <div className="form-group"><label>Nombre *</label><input name="name" value={form.name} onChange={handleChange} required /></div>
              <div className="form-group"><label>Descripción</label><textarea name="description" value={form.description} onChange={handleChange} rows={2} /></div>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1rem'}}>
                <div className="form-group"><label>Duración (min) *</label><input type="number" name="duration_minutes" value={form.duration_minutes} onChange={handleChange} min={5} required /></div>
                <div className="form-group"><label>Precio *</label><input type="number" name="price" value={form.price} onChange={handleChange} step="0.01" min={0} required /></div>
              </div>
              <div className="form-group" style={{display:'flex',alignItems:'center',gap:'.5rem'}}>
                <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} id="is_active" style={{width:'auto'}} />
                <label htmlFor="is_active" style={{marginBottom:0}}>Activo</label>
              </div>
              <div style={{display:'flex',gap:'.6rem',justifyContent:'flex-end',marginTop:'1rem'}}>
                <button type="button" className="btn-ghost" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Guardar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
