import { useEffect, useState } from 'react'
import api from '../../api.js'

const EMPTY_TENANT = {
  name: '', description: '', phone: '', address: '', city: '',
  slug: '', opening_time: '08:00', closing_time: '20:00',
  plan_id: '', is_active: true,
}

const EMPTY_ADMIN = {
  first_name: '', last_name: '', email: '', password: '', confirm_password: '', phone: '',
}

export default function AdminTenants() {
  const [tenants, setTenants]   = useState([])
  const [plans, setPlans]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [modal, setModal]       = useState(false)   // 'create' | 'edit' | null
  const [tenantForm, setTenantForm] = useState(EMPTY_TENANT)
  const [adminForm, setAdminForm]   = useState(EMPTY_ADMIN)
  const [editing, setEditing]   = useState(null)    // tenant id al editar
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

  const openCreate = () => {
    setTenantForm(EMPTY_TENANT)
    setAdminForm(EMPTY_ADMIN)
    setEditing(null)
    setModal('create')
    setFeedback(null)
  }

  const openEdit = (t) => {
    setTenantForm({
      name: t.name, description: t.description || '', phone: t.phone || '',
      address: t.address || '', city: t.city || '', slug: t.slug || '',
      opening_time: t.opening_time || '08:00', closing_time: t.closing_time || '20:00',
      plan_id: t.plan?.id || '', is_active: t.is_active,
    })
    setEditing(t.id)
    setModal('edit')
    setFeedback(null)
  }

  const handleTenantChange = e => {
    const { name, value, type, checked } = e.target
    setTenantForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleAdminChange = e => {
    setAdminForm(f => ({ ...f, [e.target.name]: e.target.value }))
  }

  const handleSubmitCreate = async (e) => {
    e.preventDefault()
    setFeedback(null)

    // Validaciones frontend
    if (!adminForm.email || !adminForm.password) {
      setFeedback('El correo y la contraseÃ±a del administrador son obligatorios.')
      return
    }
    if (adminForm.password !== adminForm.confirm_password) {
      setFeedback('Las contraseÃ±as no coinciden.')
      return
    }
    if (adminForm.password.length < 8) {
      setFeedback('La contraseÃ±a debe tener al menos 8 caracteres.')
      return
    }
    if (!tenantForm.name.trim()) {
      setFeedback('El nombre del negocio es obligatorio.')
      return
    }

    setSaving(true)
    try {
      await api.createBusinessWithAdmin({
        tenant: {
          ...tenantForm,
          plan_id: tenantForm.plan_id ? parseInt(tenantForm.plan_id) : null,
        },
        admin: {
          first_name: adminForm.first_name,
          last_name:  adminForm.last_name,
          email:      adminForm.email,
          password:   adminForm.password,
          phone:      adminForm.phone || undefined,
        },
      })
      setModal(null)
      load()
    } catch (err) {
      setFeedback(err.message)
    }
    setSaving(false)
  }

  const handleSubmitEdit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const payload = { ...tenantForm, plan_id: tenantForm.plan_id ? parseInt(tenantForm.plan_id) : null }
      await api.updateBusiness(editing, payload)
      setModal(null)
      load()
    } catch (err) {
      setFeedback(err.message)
    }
    setSaving(false)
  }

  const toggleActive = async (t) => {
    try {
      if (t.is_active) await api.deactivateTenant(t.id)
      else             await api.activateTenant(t.id)
      load()
    } catch (err) { alert(err.message) }
  }

  const planName   = (t) => t.plan?.display_name || 'â€”'
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
          <p>GestiÃ³n de tenants registrados en la plataforma</p>
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
          <div className="icon">ðŸ¢</div>
          <p>No hay negocios registrados aÃºn.</p>
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
                  <td><code className="slug-code">{t.slug || 'â€”'}</code></td>
                  <td>{t.city || 'â€”'}</td>
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

      {/* â”€â”€ Modal Crear negocio con admin â”€â”€ */}
      {modal === 'create' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Crear negocio con accesos</h3>
              <button className="modal-close" onClick={() => setModal(null)}>âœ•</button>
            </div>

            {feedback && <div className="alert alert-error" style={{ margin: '0 1.5rem 1rem' }}>{feedback}</div>}

            <form onSubmit={handleSubmitCreate} className="modal-form">
              {/* â”€â”€ Datos del negocio â”€â”€ */}
              <div style={{ padding: '0 0 .5rem', borderBottom: '1px solid var(--border)', marginBottom: '.75rem' }}>
                <strong style={{ fontSize: '.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>
                  ðŸ“‹ Datos del negocio
                </strong>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Nombre comercial *</label>
                  <input name="name" value={tenantForm.name} onChange={handleTenantChange} required placeholder="BarberÃ­a Ejemplo" />
                </div>
                <div className="form-group">
                  <label>Slug / URL *</label>
                  <input name="slug" value={tenantForm.slug} onChange={handleTenantChange} placeholder="barberia-ejemplo" />
                </div>
              </div>
              <div className="form-group">
                <label>DescripciÃ³n</label>
                <input name="description" value={tenantForm.description} onChange={handleTenantChange} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>TelÃ©fono</label>
                  <input name="phone" value={tenantForm.phone} onChange={handleTenantChange} placeholder="+57 300 000 0000" />
                </div>
                <div className="form-group">
                  <label>Ciudad</label>
                  <input name="city" value={tenantForm.city} onChange={handleTenantChange} />
                </div>
              </div>
              <div className="form-group">
                <label>DirecciÃ³n</label>
                <input name="address" value={tenantForm.address} onChange={handleTenantChange} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Horario apertura</label>
                  <input name="opening_time" type="time" value={tenantForm.opening_time} onChange={handleTenantChange} />
                </div>
                <div className="form-group">
                  <label>Horario cierre</label>
                  <input name="closing_time" type="time" value={tenantForm.closing_time} onChange={handleTenantChange} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Plan</label>
                  <select name="plan_id" value={tenantForm.plan_id} onChange={handleTenantChange}>
                    <option value="">Sin plan asignado</option>
                    {plans.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                  <div className="form-check">
                    <input type="checkbox" id="is_active_create" name="is_active" checked={tenantForm.is_active} onChange={handleTenantChange} />
                    <label htmlFor="is_active_create">Negocio activo</label>
                  </div>
                </div>
              </div>

              {/* â”€â”€ Datos del administrador â”€â”€ */}
              <div style={{ padding: '.75rem 0 .5rem', borderBottom: '1px solid var(--border)', marginBottom: '.75rem', marginTop: '.5rem' }}>
                <strong style={{ fontSize: '.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>
                  ðŸ‘¤ Administrador del negocio
                </strong>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input name="first_name" value={adminForm.first_name} onChange={handleAdminChange} required placeholder="Nombre" />
                </div>
                <div className="form-group">
                  <label>Apellido</label>
                  <input name="last_name" value={adminForm.last_name} onChange={handleAdminChange} placeholder="Apellido" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Correo electrÃ³nico *</label>
                  <input type="email" name="email" value={adminForm.email} onChange={handleAdminChange} required placeholder="admin@negocio.com" />
                </div>
                <div className="form-group">
                  <label>TelÃ©fono</label>
                  <input name="phone" value={adminForm.phone} onChange={handleAdminChange} placeholder="+57 310 000 0000" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>ContraseÃ±a inicial *</label>
                  <input type="password" name="password" value={adminForm.password} onChange={handleAdminChange} required minLength={8} placeholder="MÃ­nimo 8 caracteres" />
                </div>
                <div className="form-group">
                  <label>Confirmar contraseÃ±a *</label>
                  <input type="password" name="confirm_password" value={adminForm.confirm_password} onChange={handleAdminChange} required placeholder="Repetir contraseÃ±a" />
                </div>
              </div>

              <div style={{ background: 'var(--bg-muted)', borderRadius: '6px', padding: '.6rem .9rem', fontSize: '.8rem', color: 'var(--text-muted)', marginTop: '.25rem' }}>
                â„¹ï¸ El administrador del negocio podrÃ¡ iniciar sesiÃ³n con el correo y contraseÃ±a asignados.
                El rol <strong>tenant_admin</strong> se asigna automÃ¡ticamente.
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Creandoâ€¦' : 'Crear negocio con accesos'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* â”€â”€ Modal Editar negocio â”€â”€ */}
      {modal === 'edit' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Editar negocio</h3>
              <button className="modal-close" onClick={() => setModal(null)}>âœ•</button>
            </div>
            {feedback && <div className="alert alert-error" style={{ margin: '0 1.5rem 1rem' }}>{feedback}</div>}
            <form onSubmit={handleSubmitEdit} className="modal-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input name="name" value={tenantForm.name} onChange={handleTenantChange} required />
                </div>
                <div className="form-group">
                  <label>Slug (URL)</label>
                  <input name="slug" value={tenantForm.slug} onChange={handleTenantChange} placeholder="mi-barberia" />
                </div>
              </div>
              <div className="form-group">
                <label>DescripciÃ³n</label>
                <input name="description" value={tenantForm.description} onChange={handleTenantChange} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>TelÃ©fono</label>
                  <input name="phone" value={tenantForm.phone} onChange={handleTenantChange} />
                </div>
                <div className="form-group">
                  <label>Ciudad</label>
                  <input name="city" value={tenantForm.city} onChange={handleTenantChange} />
                </div>
              </div>
              <div className="form-group">
                <label>DirecciÃ³n</label>
                <input name="address" value={tenantForm.address} onChange={handleTenantChange} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Apertura</label>
                  <input name="opening_time" type="time" value={tenantForm.opening_time} onChange={handleTenantChange} />
                </div>
                <div className="form-group">
                  <label>Cierre</label>
                  <input name="closing_time" type="time" value={tenantForm.closing_time} onChange={handleTenantChange} />
                </div>
              </div>
              <div className="form-group">
                <label>Plan</label>
                <select name="plan_id" value={tenantForm.plan_id} onChange={handleTenantChange}>
                  <option value="">Sin plan asignado</option>
                  {plans.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
                </select>
              </div>
              <div className="form-group form-check">
                <input type="checkbox" id="is_active_edit" name="is_active" checked={tenantForm.is_active} onChange={handleTenantChange} />
                <label htmlFor="is_active_edit">Negocio activo</label>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardandoâ€¦' : 'Actualizar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

