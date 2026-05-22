import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const asItems = data => data?.items || data || []

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
  const [page,       setPage]       = useState(1)
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 20, pages: 0 })
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const params = { page, page_size: 20 }
      if (isSuperadmin && filterTenant) params.tenant_id = filterTenant
      if (search.trim()) params.search = search.trim()
      const [c, b] = await Promise.all([
        api.getClients(params),
        isSuperadmin ? api.getBusinesses({ page_size: 100 }) : Promise.resolve([]),
      ])
      setClients(asItems(c))
      setPagination(c?.items ? c : { total: (c || []).length, page: 1, page_size: (c || []).length, pages: 1 })
      if (isSuperadmin) setBusinesses(asItems(b))
      setLastUpdated(new Date())
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [filterTenant, page])
  useEffect(() => {
    const timer = setTimeout(() => { setPage(1); load() }, 350)
    return () => clearTimeout(timer)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  const businessName = (tid) => businesses.find(b => b.id === tid)?.name || `Negocio #${tid}`

  const filtered = clients

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
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
          <button className="btn btn-primary" onClick={openCreate}>+ Nuevo cliente</button>
        </div>
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
              onChange={e => { setPage(1); setFilterTenant(e.target.value) }}
              className="filter-select"
            >
              <option value="">Todos los negocios</option>
              {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          )}
        </div>
        {(search || filterTenant) && (
          <div className="action-group">
            <button type="button" className="btn btn-outline" onClick={() => { setSearch(''); setFilterTenant(''); setPage(1) }}>
              Limpiar filtros
            </button>
          </div>
        )}
      </div>

      {pagination.pages > 1 && (
        <div className="pagination-bar">
          <span>Total: {pagination.total} registros</span>
          <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</button>
          <span>Pagina {pagination.page} de {pagination.pages}</span>
          <button className="btn btn-outline btn-sm" disabled={page >= pagination.pages} onClick={() => setPage(p => p + 1)}>Siguiente</button>
        </div>
      )}

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
