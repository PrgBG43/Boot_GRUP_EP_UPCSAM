import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

export default function Clients() {
  const { user, isSuperadmin } = useAuth()
  const [clients,    setClients]    = useState([])
  const [businesses, setBusinesses] = useState([])
  const [filterTenant, setFilterTenant] = useState('')
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [modal,      setModal]      = useState(false)
  const [form,       setForm]       = useState({ full_name: '', username: '', phone: '', telegram_user_id: '' })
  const [editing,    setEditing]    = useState(null)
  const [saving,     setSaving]     = useState(false)
  const [feedback,   setFeedback]   = useState(null)
  const [search,     setSearch]     = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (isSuperadmin && filterTenant) params.tenant_id = filterTenant
      const [c, b] = await Promise.all([
        api.getClients(params),
        isSuperadmin ? api.getBusinesses() : Promise.resolve([]),
      ])
      setClients(c || [])
      if (isSuperadmin) setBusinesses(b || [])
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [filterTenant])

  const businessName = (tid) => businesses.find(b => b.id === tid)?.name || `Negocio #${tid}`

  const filtered = clients.filter(c =>
    c.full_name.toLowerCase().includes(search.toLowerCase()) ||
    (c.username || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.phone || '').includes(search)
  )

  const emptyForm = () => ({ full_name: '', username: '', phone: '', telegram_user_id: '' })

  const openCreate = () => {
    setForm(emptyForm())
    setEditing(null)
    setModal(true)
    setFeedback(null)
  }

  const openEdit = c => {
    setForm({ full_name: c.full_name, username: c.username || '', phone: c.phone || '', telegram_user_id: c.telegram_user_id || '' })
    setEditing(c.id)
    setModal(true)
    setFeedback(null)
  }

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      if (editing) {
        await api.updateClient(editing, form)
      } else {
        // tenant_id: superadmin usa el filtro seleccionado o debe elegirlo,
        // tenant_admin usa su propio tenant (el backend lo fuerza)
        const payload = { ...form }
        if (isSuperadmin && filterTenant) payload.tenant_id = parseInt(filterTenant)
        await api.createClient(payload)
      }
      setModal(false)
      load()
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Clientes finales</h1>
          <p>
            {isSuperadmin
              ? 'Clientes registrados en todos los negocios'
              : `Clientes de ${user?.tenant_name || 'tu negocio'}`}
          </p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Nuevo cliente</button>
      </div>

      {/* Filtros */}
      <div className="page-toolbar">
        <div className="filter-group">
          <input
            placeholder="Buscar por nombre, usuario o teléfono…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="search-input"
          />
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
        {(search || filterTenant) && (
          <div className="action-group">
            <button type="button" className="btn btn-outline" onClick={() => { setSearch(''); setFilterTenant('') }}>
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      <div className="table-card">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state-title">Sin clientes para mostrar</h2>
            <p className="empty-state-text">No hay clientes{search || filterTenant ? ' con los filtros aplicados.' : ' registrados.'}</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table clients-table">
              <thead>
              <tr>
                {isSuperadmin && <th>Negocio</th>}
                <th>Nombre</th>
                <th>Usuario Telegram</th>
                <th>Teléfono</th>
                <th>ID Telegram</th>
                <th>Registrado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.id}>
                  {isSuperadmin && <td><span className="cell-main">{businessName(c.tenant_id)}</span></td>}
                  <td><span className="cell-main">{c.full_name}</span></td>
                  <td className="cell-nowrap">{c.username ? `@${c.username}` : '—'}</td>
                  <td className="cell-nowrap">{c.phone || '—'}</td>
                  <td className="cell-nowrap">{c.telegram_user_id || '—'}</td>
                  <td className="cell-nowrap">{c.created_at ? new Date(c.created_at).toLocaleDateString('es-CO') : '—'}</td>
                  <td className="cell-actions">
                    <div className="table-actions">
                      <button className="btn btn-outline btn-sm" onClick={() => openEdit(c)}>Editar</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>{editing ? 'Editar cliente' : 'Nuevo cliente'}</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}
            {isSuperadmin && !editing && !filterTenant && (
              <div className="alert alert-error modal-alert">
                Selecciona un negocio en el filtro antes de crear un cliente.
              </div>
            )}
            <form onSubmit={handleSubmit} className="modal-form" noValidate>
              <div className="form-group">
                <label>Nombre completo *</label>
                <input className="form-input" name="full_name" value={form.full_name} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Usuario de Telegram</label>
                <input className="form-input" name="username" value={form.username} onChange={handleChange} placeholder="sin @" />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Teléfono</label>
                  <input className="form-input" name="phone" value={form.phone} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label>ID de Telegram</label>
                  <input className="form-input" name="telegram_user_id" value={form.telegram_user_id} onChange={handleChange} />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving || (isSuperadmin && !editing && !filterTenant)}
                >
                  {saving ? 'Guardando…' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
