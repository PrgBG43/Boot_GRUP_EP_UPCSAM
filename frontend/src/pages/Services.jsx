import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'
import BusinessAccordion from '../components/BusinessAccordion.jsx'
import { groupByBusiness } from '../utils/businessGroups.js'

const asItems = data => data?.items || data || []

export default function Services() {
  const { user, isSuperadmin, activeTenantId } = useAuth()
  const [services, setServices]   = useState([])
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [modal, setModal]         = useState(false)
  const [form, setForm]           = useState({})
  const [editing, setEditing]     = useState(null)
  const [saving, setSaving]       = useState(false)
  const [feedback, setFeedback]   = useState(null)
  const [search, setSearch]       = useState('')
  const [status, setStatus]       = useState('')
  const [page, setPage]           = useState(1)
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 20, pages: 0 })

  const emptyForm = () => ({
    tenant_id: isSuperadmin ? (activeTenantId || '') : user?.tenant_id,
    name: '', description: '', duration_minutes: 30, price: '', is_active: true,
  })

  const load = () => {
    setLoading(true)
    const params = { page, page_size: 20 }
    if (search.trim()) params.search = search.trim()
    if (status) params.status = status
    if (isSuperadmin && activeTenantId) params.tenant_id = activeTenantId
    const calls = [api.getServices(params)]
    if (isSuperadmin) calls.push(api.getBusinesses({ page_size: 100 }))
    Promise.all(calls)
      .then(([s, b]) => {
        setServices(asItems(s))
        setPagination(s?.items ? s : { total: (s || []).length, page: 1, page_size: (s || []).length, pages: 1 })
        if (b) setBusinesses(asItems(b))
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [status, page, activeTenantId])
  useEffect(() => {
    const timer = setTimeout(() => { setPage(1); load() }, 350)
    return () => clearTimeout(timer)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setPage(1) }, [activeTenantId])

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
    catch(e) { setFeedback({ type: 'error', msg: e.message }) }
  }

  const businessName = (id) => businesses.find(b => b.id === id)?.name || 'Negocio sin nombre'
  const groupedServices = isSuperadmin && !activeTenantId ? groupByBusiness(services, businesses) : []

  const renderServicesTable = (items, showBusinessColumn = isSuperadmin && !!activeTenantId) => (
    <div className="table-responsive">
      <table className="data-table services-table">
        <thead>
          <tr>
            {showBusinessColumn && <th>Negocio</th>}
            <th>Nombre</th>
            <th>Duración</th>
            <th>Precio</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map(s => (
            <tr key={s.id}>
              {showBusinessColumn && <td><span className="cell-main">{businessName(s.tenant_id)}</span></td>}
              <td>
                <span className="cell-main">{s.name}</span>
                {s.description && <span className="cell-muted">{s.description}</span>}
              </td>
              <td className="cell-nowrap">{s.duration_minutes} min</td>
              <td className="cell-nowrap">${Number(s.price).toLocaleString('es-CO')}</td>
              <td>
                <span className={`badge ${s.is_active ? 'badge-success' : 'badge-neutral'}`}>
                  {s.is_active ? 'Activo' : 'Inactivo'}
                </span>
              </td>
              <td className="cell-actions">
                <div className="table-actions">
                  <button className="btn btn-outline btn-sm" onClick={() => openEdit(s)}>Editar</button>
                  <button
                    className={`btn btn-sm ${s.is_active ? 'btn-danger' : 'btn-success'}`}
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
    </div>
  )

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Servicios</h1>
          <p>{isSuperadmin && !activeTenantId ? 'Servicios agrupados por negocio' : 'Gestiona los servicios ofrecidos por el negocio'}</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Nuevo servicio</button>
      </div>

      <div className="page-toolbar">
        <div className="filter-group">
          <input className="search-input" placeholder="Buscar servicio..." value={search} onChange={e => setSearch(e.target.value)} />
          <select className="filter-select" value={status} onChange={e => { setPage(1); setStatus(e.target.value) }}>
            <option value="">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
          </select>
        </div>
      </div>

      <div className="table-card">
        {services.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state-title">Sin servicios registrados</h2>
            <p className="empty-state-text">Crea el primer servicio para habilitar la agenda del negocio.</p>
            <button className="btn btn-primary empty-state-action" onClick={openCreate}>Crear primer servicio</button>
          </div>
        ) : isSuperadmin && !activeTenantId ? (
          <BusinessAccordion
            groups={groupedServices}
            itemLabel={{ singular: 'servicio', plural: 'servicios' }}
            emptyTitle="Sin servicios registrados"
            emptyText="Crea el primer servicio para habilitar la agenda del negocio."
            renderGroup={group => renderServicesTable(group.items, false)}
          />
        ) : (
          renderServicesTable(services, isSuperadmin)
        )}
      </div>

      {pagination.pages > 1 && (
        <div className="pagination-bar">
          <span>Total: {pagination.total} registros</span>
          <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</button>
          <span>Página {pagination.page} de {pagination.pages}</span>
          <button className="btn btn-outline btn-sm" disabled={page >= pagination.pages} onClick={() => setPage(p => p + 1)}>Siguiente</button>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>{editing ? 'Editar servicio' : 'Nuevo servicio'}</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type} modal-alert`}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit} className="modal-form" noValidate>
              {isSuperadmin && (
                <div className="form-group">
                  <label>Negocio *</label>
                  <select className="form-select" name="tenant_id" value={form.tenant_id} onChange={handleChange} disabled={!!activeTenantId}>
                    <option value="">Selecciona un negocio</option>
                    {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>Nombre *</label>
                <input className="form-input" name="name" value={form.name} onChange={handleChange} placeholder="Ej: Corte de cabello" />
              </div>
              <div className="form-group">
                <label>Descripción</label>
                <textarea className="form-textarea" name="description" value={form.description} onChange={handleChange} rows={2} placeholder="Descripción breve del servicio" />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Duración (min) *</label>
                  <input className="form-input" type="number" name="duration_minutes" value={form.duration_minutes} onChange={handleChange} min={5} />
                </div>
                <div className="form-group">
                  <label>Precio (COP) *</label>
                  <input className="form-input" type="number" name="price" value={form.price} onChange={handleChange} step="0.01" min={0} />
                </div>
              </div>
              <div className="form-group form-check">
                <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} id="svc_active" />
                <label htmlFor="svc_active">Servicio activo</label>
              </div>
            </form>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
              <button type="button" className="btn btn-primary" disabled={saving || (isSuperadmin && !form.tenant_id)} onClick={handleSubmit}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
