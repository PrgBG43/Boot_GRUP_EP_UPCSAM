import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'
import api from '../../api.js'
import { ROLE_OPTIONS, roleBadgeClass, roleLabel } from '../../utils/labels.js'

const ROLES = ROLE_OPTIONS.map(option => option.value)
const asItems = data => data?.items || data || []

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', password: '',
  phone: '', role_name: 'staff', tenant_id: '',
}

function RolePill({ role }) {
  return <span className={`badge badge-role ${roleBadgeClass(role)}`}>{roleLabel(role)}</span>
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
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 20, pages: 0 })
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterTenant && filterTenant !== "") params.tenant_id = filterTenant
      if (search.trim()) params.search = search.trim()
      if (filterRole) params.role = filterRole
      params.page = page
      params.page_size = 20
      
      const [u, b] = await Promise.all([api.getUsers(params), api.getBusinesses({ page_size: 100 })])
      setUsers(asItems(u))
      setPagination(u?.items ? u : { total: (u || []).length, page: 1, page_size: (u || []).length, pages: 1 })
      setBusinesses(asItems(b))
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [filterTenant, filterRole, page])
  useEffect(() => {
    const timer = setTimeout(() => { setPage(1); load() }, 350)
    return () => clearTimeout(timer)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  const tenantName = (id) => businesses.find(b => b.id === id)?.name || `Negocio #${id}`

  const filtered = users

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
    setConfirmPassword('')
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
    if (!newPassword || newPassword.length < 8) {
      setFeedback({ type: 'error', msg: 'La contraseña debe tener mínimo 8 caracteres.' })
      return
    }
    if (newPassword !== confirmPassword) {
      setFeedback({ type: 'error', msg: 'Las contraseñas no coinciden.' })
      return
    }
    setSaving(true); setFeedback(null)
    try {
      await api.resetPassword(selected.id, { new_password: newPassword, confirm_password: confirmPassword })
      setModal(null)
      setFeedback({ type: 'success', msg: 'Contraseña actualizada.' })
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
    } catch (e) { setFeedback({ type: 'error', msg: e.message }) }
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
      <div className="page-toolbar">
        <div className="filter-group">
            <input
              className="search-input users-search"
              placeholder="Buscar por nombre o correo..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <select className="filter-select" value={filterRole} onChange={e => { setPage(1); setFilterRole(e.target.value) }}>
              <option value="">Todos los roles</option>
              {ROLES.map(r => <option key={r} value={r}>{roleLabel(r)}</option>)}
            </select>
            <select className="filter-select" value={filterTenant} onChange={e => { setPage(1); setFilterTenant(e.target.value) }}>
              <option value="">Todos los negocios</option>
              {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
        </div>
      </div>

      {pagination.pages > 1 && (
        <div className="pagination-bar">
          <span>Total: {pagination.total} registros</span>
          <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</button>
          <span>Página {pagination.page} de {pagination.pages}</span>
          <button className="btn btn-outline btn-sm" disabled={page >= pagination.pages} onClick={() => setPage(p => p + 1)}>Siguiente</button>
        </div>
      )}

      <div className="table-card">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state-title">Sin usuarios para mostrar</h2>
            <p className="empty-state-text">No se encontraron usuarios con los filtros aplicados.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table users-table">
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
                    <td><span className="cell-main">{u.first_name || u.last_name ? `${u.first_name || ''} ${u.last_name || ''}`.trim() : '—'}</span></td>
                    <td><span className="cell-email">{u.email}</span></td>
                    <td><RolePill role={u.role} /></td>
                    <td>{u.tenant_id ? <span className="cell-nowrap">{tenantName(u.tenant_id)}</span> : <span className="cell-muted">Global</span>}</td>
                    <td>
                      <span className={`badge ${u.is_active ? 'badge-success' : 'badge-neutral'}`}>
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="cell-actions">
                      <div className="table-actions">
                        <button className="btn btn-sm btn-outline" onClick={() => openEdit(u)}>Editar</button>
                        <button className="btn btn-sm btn-secondary" onClick={() => openReset(u)}>Restablecer</button>
                        {u.id !== me?.id && (
                          <button
                            className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`}
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
              <button className="modal-close" onClick={() => setModal(null)}>×</button>
            </div>
            <form onSubmit={handleCreate} className="modal-form" noValidate>
              <div className="modal-body">
                <div className="modal-section-header">Datos personales</div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Nombre *</label>
                    <input className="form-input" name="first_name" value={form.first_name} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Apellido</label>
                    <input className="form-input" name="last_name" value={form.last_name} onChange={handleChange} />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Teléfono</label>
                    <input className="form-input" name="phone" value={form.phone} onChange={handleChange} />
                  </div>
                </div>

                <div className="modal-section-header modal-section-header-spaced">Acceso</div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Correo electrónico *</label>
                    <input className="form-input" type="email" name="email" value={form.email} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Contraseña *</label>
                    <input className="form-input" type="password" name="password" value={form.password} onChange={handleChange} placeholder="Mínimo 8 caracteres" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Rol *</label>
                    <select className="form-select" name="role_name" value={form.role_name} onChange={handleChange}>
                      {ROLES.map(r => <option key={r} value={r}>{roleLabel(r)}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Negocio</label>
                    <select className="form-select" name="tenant_id" value={form.tenant_id} onChange={handleChange}>
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
                  {saving ? 'Guardando...' : 'Crear usuario'}
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
              <button className="modal-close" onClick={() => setModal(null)}>×</button>
            </div>
            <form onSubmit={handleEdit} className="modal-form" noValidate>
              <div className="modal-body">
                <div className="form-group">
                  <label>Correo electrónico</label>
                  <input className="form-input" type="email" name="email" value={form.email} onChange={handleChange} />
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
                  {saving ? 'Guardando...' : 'Guardar cambios'}
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
              <button className="modal-close" onClick={() => setModal(null)}>×</button>
            </div>
            <form onSubmit={handleResetPassword} noValidate>
              <div className="modal-body">
                <p className="modal-helper-text">
                  Cambiando contraseña de <strong>{selected.email}</strong>
                </p>
                <div className="form-group">
                  <label>Nueva contraseña *</label>
                  <input
                    className="form-control"
                    type="password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="Mínimo 8 caracteres"
                  />
                </div>
                <div className="form-group">
                  <label>Confirmar nueva contraseña *</label>
                  <input
                    className="form-control"
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="Repetir contraseña"
                  />
                </div>
                {feedback && (
                  <div className={`alert alert-${feedback.type === 'error' ? 'error' : 'success'}`}>{feedback.msg}</div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando...' : 'Cambiar contraseña'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
