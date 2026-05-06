import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'
import api from '../../api.js'

const ROLES = ['superadmin', 'tenant_admin', 'staff', 'customer']

const ROLE_LABELS = {
  superadmin:   { label: 'Superadmin',    cls: 'role-superadmin' },
  tenant_admin: { label: 'Administrador', cls: 'role-admin' },
  staff:        { label: 'Personal',      cls: 'role-staff' },
  customer:     { label: 'Cliente',       cls: 'role-customer' },
}

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', password: '',
  phone: '', role_name: 'staff', tenant_id: '',
}

function RolePill({ role }) {
  const r = ROLE_LABELS[role] || { label: role, cls: '' }
  return <span className={`role-pill ${r.cls}`}>{r.label}</span>
}

export default function AdminUsers() {
  const { user: me } = useAuth()
  const [users,      setUsers]     = useState([])
  const [businesses, setBusinesses] = useState([])
  const [loading,    setLoading]   = useState(true)
  const [error,      setError]     = useState(null)
  const [modal,      setModal]     = useState(null) // 'create' | 'edit' | 'reset'
  const [selected,   setSelected]  = useState(null)
  const [form,       setForm]      = useState(EMPTY_FORM)
  const [saving,     setSaving]    = useState(false)
  const [feedback,   setFeedback]  = useState(null)
  const [search,     setSearch]    = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [filterTenant, setFilterTenant] = useState('')
  const [newPassword, setNewPassword] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterTenant) params.tenant_id = filterTenant
      const [u, b] = await Promise.all([api.getUsers(params), api.getBusinesses()])
      setUsers(u || [])
      setBusinesses(b || [])
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [filterTenant])

  const tenantName = (id) => businesses.find(b => b.id === id)?.name || `Negocio #${id}`

  const filtered = users.filter(u => {
    const name = `${u.first_name || ''} ${u.last_name || ''} ${u.email}`.toLowerCase()
    const matchSearch = name.includes(search.toLowerCase())
    const matchRole   = !filterRole   || u.role === filterRole
    return matchSearch && matchRole
  })

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setSelected(null)
    setFeedback(null)
    setModal('create')
  }

  const openEdit = (u) => {
    setForm({
      first_name: u.first_name || '',
      last_name:  u.last_name  || '',
      email:      u.email,
      password:   '',
      phone:      '',
      role_name:  u.role || 'staff',
      tenant_id:  u.tenant_id || '',
    })
    setSelected(u)
    setFeedback(null)
    setModal('edit')
  }

  const openReset = (u) => {
    setSelected(u)
    setNewPassword('')
    setFeedback(null)
    setModal('reset')
  }

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleCreate = async e => {
    e.preventDefault()
    setSaving(true); setFeedback(null)
    try {
      await api.createUser({
        ...form,
        tenant_id: form.tenant_id ? parseInt(form.tenant_id) : null,
      })
      setModal(null)
      load()
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const handleEdit = async e => {
    e.preventDefault()
    setSaving(true); setFeedback(null)
    try {
      const payload = { email: form.email, is_active: selected.is_active }
      if (form.password) payload.password = form.password
      await api.updateUser(selected.id, payload)
      setModal(null)
      load()
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const handleResetPassword = async e => {
    e.preventDefault()
    if (!newPassword || newPassword.length < 6) {
      setFeedback({ type: 'error', msg: 'La contraseña debe tener al menos 6 caracteres' })
      return
    }
    setSaving(true); setFeedback(null)
    try {
      await api.updateUser(selected.id, { password: newPassword })
      setModal(null)
      setFeedback({ type: 'success', msg: 'Contraseña actualizada' })
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const toggleActive = async (u) => {
    try {
      if (u.is_active) await api.deactivateUser(u.id)
      else             await api.activateUser(u.id)
      load()
    } catch (e) { alert(e.message) }
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Usuarios</h1>
          <p>Gestiona todos los usuarios de la plataforma</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Nuevo usuario</button>
      </div>

      {/* Filtros */}
      <div className="card" style={{ marginBottom: '1rem', padding: '.75rem 1rem' }}>
        <div className="form-row" style={{ alignItems: 'flex-end', gap: '.75rem' }}>
          <div className="form-group" style={{ flex: 2, margin: 0 }}>
            <input
              className="form-control"
              placeholder="Buscar por nombre o correo…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="form-group" style={{ flex: 1, margin: 0 }}>
            <select className="form-control" value={filterRole} onChange={e => setFilterRole(e.target.value)}>
              <option value="">Todos los roles</option>
              {ROLES.map(r => <option key={r} value={r}>{ROLE_LABELS[r]?.label || r}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ flex: 1, margin: 0 }}>
            <select className="form-control" value={filterTenant} onChange={e => setFilterTenant(e.target.value)}>
              <option value="">Todos los negocios</option>
              {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="icon">🔑</div>
            <p>No se encontraron usuarios.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th>Negocio</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(u => (
                  <tr key={u.id}>
                    <td>{u.first_name || u.last_name ? `${u.first_name || ''} ${u.last_name || ''}`.trim() : '—'}</td>
                    <td>{u.email}</td>
                    <td><RolePill role={u.role} /></td>
                    <td>{u.tenant_id ? tenantName(u.tenant_id) : <span className="text-muted">Global</span>}</td>
                    <td>
                      <span className={`badge ${u.is_active ? 'badge-confirmed' : 'badge-cancelled'}`}>
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap' }}>
                        <button className="btn btn-sm btn-outline" onClick={() => openEdit(u)}>Editar</button>
                        <button className="btn btn-sm btn-outline" onClick={() => openReset(u)}>Reset pwd</button>
                        {u.id !== me?.id && (
                          <button
                            className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-outline'}`}
                            onClick={() => toggleActive(u)}
                          >
                            {u.is_active ? 'Desactivar' : 'Activar'}
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

      {/* Modal crear */}
      {modal === 'create' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Nuevo usuario</h3>
              <button className="modal-close" onClick={() => setModal(null)}>✕</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                <div className="modal-section-header">Datos personales</div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Nombre *</label>
                    <input className="form-control" name="first_name" required value={form.first_name} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Apellido</label>
                    <input className="form-control" name="last_name" value={form.last_name} onChange={handleChange} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Teléfono</label>
                    <input className="form-control" name="phone" value={form.phone} onChange={handleChange} />
                  </div>
                </div>

                <div className="modal-section-header" style={{ marginTop: '1rem' }}>Acceso</div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Correo electrónico *</label>
                    <input className="form-control" type="email" name="email" required value={form.email} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Contraseña *</label>
                    <input className="form-control" type="password" name="password" required value={form.password} onChange={handleChange} placeholder="Mínimo 6 caracteres" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Rol *</label>
                    <select className="form-control" name="role_name" value={form.role_name} onChange={handleChange}>
                      {ROLES.map(r => <option key={r} value={r}>{ROLE_LABELS[r]?.label || r}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Negocio</label>
                    <select className="form-control" name="tenant_id" value={form.tenant_id} onChange={handleChange}>
                      <option value="">Sin negocio (global)</option>
                      {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                    </select>
                  </div>
                </div>
                {feedback && (
                  <div className={`alert alert-${feedback.type === 'error' ? 'error' : 'success'}`}>{feedback.msg}</div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando…' : 'Crear usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal editar */}
      {modal === 'edit' && selected && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Editar usuario</h3>
              <button className="modal-close" onClick={() => setModal(null)}>✕</button>
            </div>
            <form onSubmit={handleEdit}>
              <div className="modal-body">
                <div className="form-group">
                  <label>Correo electrónico</label>
                  <input className="form-control" type="email" name="email" required value={form.email} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>Rol</label>
                  <div className="form-control-static"><RolePill role={selected.role} /></div>
                  <small className="text-muted">El rol no se puede cambiar desde aquí.</small>
                </div>
                <div className="form-group">
                  <label>Negocio asignado</label>
                  <div className="form-control-static">
                    {selected.tenant_id ? tenantName(selected.tenant_id) : 'Sin negocio (global)'}
                  </div>
                </div>
                {feedback && (
                  <div className={`alert alert-${feedback.type === 'error' ? 'error' : 'success'}`}>{feedback.msg}</div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando…' : 'Guardar cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal reset contraseña */}
      {modal === 'reset' && selected && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Restablecer contraseña</h3>
              <button className="modal-close" onClick={() => setModal(null)}>✕</button>
            </div>
            <form onSubmit={handleResetPassword}>
              <div className="modal-body">
                <p style={{ marginBottom: '.75rem', color: 'var(--text-secondary)' }}>
                  Cambiando contraseña de <strong>{selected.email}</strong>
                </p>
                <div className="form-group">
                  <label>Nueva contraseña *</label>
                  <input
                    className="form-control"
                    type="password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                    required
                  />
                </div>
                {feedback && (
                  <div className={`alert alert-${feedback.type === 'error' ? 'error' : 'success'}`}>{feedback.msg}</div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando…' : 'Cambiar contraseña'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
