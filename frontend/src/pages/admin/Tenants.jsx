import { useEffect, useState } from 'react'
import api from '../../api.js'

const EMPTY_FORM = {
  name: '', description: '', phone: '', address: '', city: '',
  slug: '', opening_time: '08:00', closing_time: '20:00',
  plan_id: '', is_active: true,
}

export default function AdminTenants() {
  const [tenants, setTenants]   = useState([])
  const [plans, setPlans]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [modal, setModal]       = useState(false)
  const [form, setForm]         = useState(EMPTY_FORM)
  const [editing, setEditing]   = useState(null)
  const [saving, setSaving]     = useState(false)
  const [feedback, setFeedback] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [t, p] = await Promise.all([api.getBusinesses(), api.getPlans()])
      setTenants(t || [])
      setPlans(p || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openCreate = () => { setForm(EMPTY_FORM); setEditing(null); setModal(true); setFeedback(null) }
  const openEdit   = (t) => {
    setForm({
      name: t.name, description: t.description || '', phone: t.phone || '',
      address: t.address || '', city: t.city || '', slug: t.slug || '',
      opening_time: t.opening_time || '08:00', closing_time: t.closing_time || '20:00',
      plan_id: t.plan?.id || '', is_active: t.is_active,
    })
    setEditing(t.id); setModal(true); setFeedback(null)
  }

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      const payload = { ...form, plan_id: form.plan_id ? parseInt(form.plan_id) : null }
      if (editing) await api.updateBusiness(editing, payload)
      else         await api.createBusiness(payload)
      setModal(false); load()
    } catch (err) { setFeedback(err.message) }
    setSaving(false)
  }

  const toggleActive = async (t) => {
    try {
      if (t.is_active) await api.deactivateTenant(t.id)
      else             await api.activateTenant(t.id)
      load()
    } catch (err) { alert(err.message) }
  }

  const planName = (t) => t.plan?.display_name || '—'
  const statusBadge = (active) => (
    <span className={`badge badge-${active ? 'confirmed' : 'cancelled'}`}>
      {active ? 'Activo' : 'Inactivo'}
    </span>
  )

  if (loading) return <div className="spinner" />

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Negocios</h1>
          <p>Gestión de tenants registrados en la plataforma</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Nuevo negocio</button>
      </div>

      <div className="stats-row">
        <div className="mini-stat"><strong>{tenants.length}</strong><span>Total</span></div>
        <div className="mini-stat"><strong>{tenants.filter(t => t.is_active).length}</strong><span>Activos</span></div>
        <div className="mini-stat"><strong>{tenants.filter(t => !t.is_active).length}</strong><span>Inactivos</span></div>
      </div>

      {tenants.length === 0 ? (
        <div className="empty-state">
          <div className="icon">🏢</div>
          <p>No hay negocios registrados aún.</p>
          <button className="btn btn-primary" onClick={openCreate}>Crear primer negocio</button>
        </div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Negocio</th>
                <th>Slug</th>
                <th>Ciudad</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map(t => (
                <tr key={t.id}>
                  <td>
                    <strong>{t.name}</strong>
                    {t.description && <div className="table-sub">{t.description}</div>}
                  </td>
                  <td><code className="slug-code">{t.slug || '—'}</code></td>
                  <td>{t.city || '—'}</td>
                  <td><span className="plan-pill">{planName(t)}</span></td>
                  <td>{statusBadge(t.is_active)}</td>
                  <td>
                    <div className="table-actions">
                      <button className="btn-sm btn-outline" onClick={() => openEdit(t)}>Editar</button>
                      <button
                        className={`btn-sm ${t.is_active ? 'btn-danger-sm' : 'btn-success-sm'}`}
                        onClick={() => toggleActive(t)}
                      >
                        {t.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editing ? 'Editar negocio' : 'Nuevo negocio'}</h3>
              <button className="modal-close" onClick={() => setModal(false)}>✕</button>
            </div>
            {feedback && <div className="alert alert-error">{feedback}</div>}
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input name="name" value={form.name} onChange={handleChange} required />
                </div>
                <div className="form-group">
                  <label>Slug (URL)</label>
                  <input name="slug" value={form.slug} onChange={handleChange} placeholder="mi-barberia" />
                </div>
              </div>
              <div className="form-group">
                <label>Descripción</label>
                <input name="description" value={form.description} onChange={handleChange} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Teléfono</label>
                  <input name="phone" value={form.phone} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>Ciudad</label>
                  <input name="city" value={form.city} onChange={handleChange} />
                </div>
              </div>
              <div className="form-group">
                <label>Dirección</label>
                <input name="address" value={form.address} onChange={handleChange} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Apertura</label>
                  <input name="opening_time" type="time" value={form.opening_time} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>Cierre</label>
                  <input name="closing_time" type="time" value={form.closing_time} onChange={handleChange} />
                </div>
              </div>
              <div className="form-group">
                <label>Plan</label>
                <select name="plan_id" value={form.plan_id} onChange={handleChange}>
                  <option value="">Sin plan asignado</option>
                  {plans.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
                </select>
              </div>
              <div className="form-group form-check">
                <input type="checkbox" id="is_active" name="is_active" checked={form.is_active} onChange={handleChange} />
                <label htmlFor="is_active">Negocio activo</label>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando…' : editing ? 'Actualizar' : 'Crear negocio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
