import { useEffect, useState } from 'react'
import api from '../api.js'

const EMPTY_FORM = { name: '', description: '', phone: '', address: '', opening_time: '08:00', closing_time: '20:00', is_active: true }

export default function BusinessConfig() {
  const [businesses, setBusinesses] = useState([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [modal,      setModal]      = useState(false)
  const [form,       setForm]       = useState(EMPTY_FORM)
  const [editing,    setEditing]    = useState(null)
  const [saving,     setSaving]     = useState(false)
  const [feedback,   setFeedback]   = useState(null)

  const load = () => {
    setLoading(true)
    api.getBusinesses()
      .then(b => { setBusinesses(b || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [])

  const openCreate = () => { setForm(EMPTY_FORM); setEditing(null); setModal(true); setFeedback(null) }
  const openEdit   = b  => {
    setForm({ name: b.name, description: b.description || '', phone: b.phone || '', address: b.address || '', opening_time: b.opening_time || '08:00', closing_time: b.closing_time || '20:00', is_active: b.is_active })
    setEditing(b.id); setModal(true); setFeedback(null)
  }

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      if (editing) await api.updateBusiness(editing, form)
      else          await api.createBusiness(form)
      setModal(false); load()
      setFeedback({ type: 'success', msg: editing ? 'Negocio actualizado.' : 'Negocio creado.' })
    } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
    setSaving(false)
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <h1>Configuración del Negocio</h1>
        <p>Administra los datos del negocio y su horario</p>
      </div>

      {feedback && !modal && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}

      <div className="actions-bar">
        <div />
        <button className="btn-primary" onClick={openCreate}>+ Nuevo negocio</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: '1.25rem' }}>
        {businesses.length === 0 ? (
          <div className="card empty-state"><div className="icon">🏪</div><p>No hay negocios registrados.</p></div>
        ) : businesses.map(b => (
          <div key={b.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '.25rem' }}>{b.name}</h3>
                <span className={`badge badge-${b.is_active ? 'active' : 'inactive'}`}>{b.is_active ? 'Activo' : 'Inactivo'}</span>
              </div>
              <button className="btn-ghost btn-sm" onClick={() => openEdit(b)}>Editar</button>
            </div>
            {b.description && <p style={{ marginTop: '.75rem', fontSize: '.88rem', color: 'var(--text-muted)' }}>{b.description}</p>}
            <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.5rem', fontSize: '.85rem' }}>
              <div><strong>📞</strong> {b.phone || '—'}</div>
              <div><strong>📍</strong> {b.address || '—'}</div>
              <div><strong>🕗 Apertura:</strong> {b.opening_time || '—'}</div>
              <div><strong>🕗 Cierre:</strong> {b.closing_time || '—'}</div>
            </div>
          </div>
        ))}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>{editing ? 'Editar negocio' : 'Nuevo negocio'}</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group"><label>Nombre *</label><input name="name" value={form.name} onChange={handleChange} required /></div>
              <div className="form-group"><label>Descripción</label><textarea name="description" value={form.description} onChange={handleChange} rows={2} /></div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group"><label>Teléfono</label><input name="phone" value={form.phone} onChange={handleChange} /></div>
                <div className="form-group"><label>Dirección</label><input name="address" value={form.address} onChange={handleChange} /></div>
                <div className="form-group"><label>Hora apertura</label><input type="time" name="opening_time" value={form.opening_time} onChange={handleChange} /></div>
                <div className="form-group"><label>Hora cierre</label><input type="time" name="closing_time" value={form.closing_time} onChange={handleChange} /></div>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
                <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} id="biz_active" style={{ width: 'auto' }} />
                <label htmlFor="biz_active" style={{ marginBottom: 0 }}>Activo</label>
              </div>
              <div style={{ display: 'flex', gap: '.6rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
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
