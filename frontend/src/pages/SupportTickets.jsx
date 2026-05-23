import { useEffect, useState } from 'react'
import api from '../api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { planLabel, statusBadgeClass, statusLabel } from '../utils/labels.js'

const asItems = data => data?.items || data || []

const PRIORITIES = [
  { value: 'low', label: 'Baja' },
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'Alta' },
  { value: 'urgent', label: 'Urgente' },
]

const STATUSES = [
  { value: 'open', label: 'Abierto' },
  { value: 'in_progress', label: 'En proceso' },
  { value: 'waiting_user', label: 'Esperando respuesta' },
  { value: 'resolved', label: 'Resuelto' },
  { value: 'closed', label: 'Cerrado' },
]

const CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'appointments', label: 'Citas' },
  { value: 'billing', label: 'Plan y facturación' },
  { value: 'technical', label: 'Problema técnico' },
]

const emptyForm = {
  tenant_id: '',
  subject: '',
  category: 'general',
  priority: 'normal',
  description: '',
}

function priorityLabel(value) {
  return PRIORITIES.find(item => item.value === value)?.label || statusLabel(value)
}

function categoryLabel(value) {
  return CATEGORIES.find(item => item.value === value)?.label || 'General'
}

function ticketStatusLabel(value) {
  return STATUSES.find(item => item.value === value)?.label || statusLabel(value)
}

export default function SupportTickets() {
  const { isSuperadmin } = useAuth()
  const [tickets, setTickets] = useState([])
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [selected, setSelected] = useState(null)
  const [reply, setReply] = useState('')
  const [sending, setSending] = useState(false)
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')
  const [filterPlan, setFilterPlan] = useState('')
  const [filterTenant, setFilterTenant] = useState('')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 20, pages: 0 })

  const load = async () => {
    setLoading(true)
    try {
      const params = { page, page_size: 20 }
      if (search.trim()) params.search = search.trim()
      if (filterStatus) params.status = filterStatus
      if (filterPriority) params.priority = filterPriority
      if (isSuperadmin && filterPlan) params.plan = filterPlan
      if (isSuperadmin && filterTenant) params.tenant_id = filterTenant
      const [ticketData, businessData] = await Promise.all([
        api.getSupportTickets(params),
        isSuperadmin ? api.getBusinesses({ page_size: 100 }) : Promise.resolve([]),
      ])
      setTickets(asItems(ticketData))
      setPagination(ticketData?.items ? ticketData : { total: (ticketData || []).length, page: 1, page_size: (ticketData || []).length, pages: 1 })
      if (isSuperadmin) setBusinesses(asItems(businessData))
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err.message || 'No fue posible cargar los tickets.')
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [filterStatus, filterPriority, filterPlan, filterTenant, page]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const timer = setTimeout(() => { setPage(1); load() }, 350)
    return () => clearTimeout(timer)
  }, [search]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selected) return undefined
    const timer = setInterval(() => refreshTicket(selected.id, true), 10000)
    return () => clearInterval(timer)
  }, [selected]) // eslint-disable-line react-hooks/exhaustive-deps

  const refreshTicket = async (id, silent = false) => {
    try {
      const ticket = await api.getSupportTicket(id)
      setSelected(ticket)
      if (!silent) setFeedback(null)
    } catch (err) {
      if (!silent) setFeedback({ type: 'error', msg: err.message })
    }
  }

  const openTicket = async (ticket) => {
    setReply('')
    await refreshTicket(ticket.id)
  }

  const openCreate = () => {
    setForm(emptyForm)
    setFeedback(null)
    setModal(true)
  }

  const handleFormChange = (event) => {
    const { name, value } = event.target
    setForm(current => ({ ...current, [name]: value }))
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const payload = { ...form }
      if (!isSuperadmin) delete payload.tenant_id
      else payload.tenant_id = parseInt(payload.tenant_id)
      const created = await api.createSupportTicket(payload)
      setModal(false)
      setForm(emptyForm)
      await load()
      await refreshTicket(created.id)
      setFeedback({ type: 'success', msg: 'Ticket creado correctamente.' })
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    }
    setSaving(false)
  }

  const handleReply = async (event) => {
    event.preventDefault()
    const message = reply.trim()
    if (!selected || !message) return
    setSending(true)
    setFeedback(null)
    try {
      await api.addSupportTicketMessage(selected.id, { message })
      setReply('')
      await refreshTicket(selected.id, true)
      await load()
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    }
    setSending(false)
  }

  const changeStatus = async (ticket, nextStatus) => {
    try {
      const updated = await api.updateSupportTicket(ticket.id, { status: nextStatus })
      setSelected(current => current?.id === ticket.id ? updated : current)
      await load()
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    }
  }

  const closeTicket = async (ticket) => {
    try {
      const updated = await api.closeSupportTicket(ticket.id)
      setSelected(current => current?.id === ticket.id ? updated : current)
      await load()
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    }
  }

  const reopenTicket = async (ticket) => {
    try {
      const updated = await api.reopenSupportTicket(ticket.id)
      setSelected(current => current?.id === ticket.id ? updated : current)
      await load()
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    }
  }

  const clearFilters = () => {
    setSearch('')
    setFilterStatus('')
    setFilterPriority('')
    setFilterPlan('')
    setFilterTenant('')
    setPage(1)
  }

  if (loading && tickets.length === 0) return <div className="spinner" />
  if (error) return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{isSuperadmin ? 'Soporte de la plataforma' : 'Ayuda y soporte'}</h1>
          <p>{isSuperadmin ? 'Gestiona solicitudes de todos los negocios' : 'Abre solicitudes y conversa con soporte de Turnix'}</p>
        </div>
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
          <button className="btn btn-primary" onClick={openCreate}>Crear ticket</button>
        </div>
      </div>

      {feedback && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}

      <div className="page-toolbar">
        <div className="filter-group">
          <input
            className="search-input"
            placeholder="Buscar ticket, negocio o descripción..."
            value={search}
            onChange={event => setSearch(event.target.value)}
          />
          <select className="filter-select" value={filterStatus} onChange={event => { setPage(1); setFilterStatus(event.target.value) }}>
            <option value="">Todos los estados</option>
            {STATUSES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <select className="filter-select" value={filterPriority} onChange={event => { setPage(1); setFilterPriority(event.target.value) }}>
            <option value="">Todas las prioridades</option>
            {PRIORITIES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          {isSuperadmin && (
            <>
              <select className="filter-select" value={filterPlan} onChange={event => { setPage(1); setFilterPlan(event.target.value) }}>
                <option value="">Todos los planes</option>
                <option value="free">Gratuito</option>
                <option value="premium">Premium</option>
              </select>
              <select className="filter-select" value={filterTenant} onChange={event => { setPage(1); setFilterTenant(event.target.value) }}>
                <option value="">Todos los negocios</option>
                {businesses.map(business => <option key={business.id} value={business.id}>{business.name}</option>)}
              </select>
            </>
          )}
        </div>
        {(search || filterStatus || filterPriority || filterPlan || filterTenant) && (
          <div className="action-group">
            <button className="btn btn-outline" type="button" onClick={clearFilters}>Limpiar filtros</button>
          </div>
        )}
      </div>

      <div className={`surface-grid${selected ? ' surface-grid--split' : ''}`}>
        <div className="table-card">
          {tickets.length === 0 ? (
            <div className="empty-state">
              <h2 className="empty-state-title">Sin tickets para mostrar</h2>
              <p className="empty-state-text">No hay solicitudes con los filtros actuales.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table support-table">
                <thead>
                  <tr>
                    <th>Ticket</th>
                    {isSuperadmin && <th>Negocio</th>}
                    <th>Asunto</th>
                    <th>Prioridad</th>
                    <th>Estado</th>
                    <th>Actualizado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map(ticket => (
                    <tr key={ticket.id} className="clickable-row" onClick={() => openTicket(ticket)}>
                      <td className="cell-nowrap">#{ticket.id}</td>
                      {isSuperadmin && (
                        <td>
                          <span className="cell-main">{ticket.tenant_name || 'Sin información'}</span>
                          {ticket.is_premium && <span className="badge badge-premium">Prioridad Premium</span>}
                          {!ticket.is_premium && <span className="cell-muted">{planLabel(ticket.tenant_plan)}</span>}
                        </td>
                      )}
                      <td>
                        <span className="cell-main">{ticket.subject}</span>
                        <span className="cell-muted">{categoryLabel(ticket.category)}</span>
                      </td>
                      <td><span className={`badge ${statusBadgeClass(ticket.priority)}`}>{priorityLabel(ticket.priority)}</span></td>
                      <td><span className={`badge ${statusBadgeClass(ticket.status)}`}>{ticketStatusLabel(ticket.status)}</span></td>
                      <td className="cell-nowrap">{ticket.updated_at ? new Date(ticket.updated_at).toLocaleString('es-CO') : 'Sin información'}</td>
                      <td className="cell-actions">
                        <div className="table-actions">
                          <button className="btn btn-outline btn-sm" onClick={(event) => { event.stopPropagation(); openTicket(ticket) }}>Ver</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {selected && (
          <div className="card support-detail">
            <div className="card-header-row">
              <div>
                <h3>Ticket #{selected.id}</h3>
                <span className="chat-subtitle">{selected.subject}</span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setSelected(null)}>Cerrar</button>
            </div>
            <div className="support-meta">
              <span className={`badge ${statusBadgeClass(selected.status)}`}>{ticketStatusLabel(selected.status)}</span>
              <span className={`badge ${statusBadgeClass(selected.priority)}`}>{priorityLabel(selected.priority)}</span>
              {selected.is_premium && <span className="badge badge-premium">Prioridad Premium</span>}
              <span className="badge badge-neutral">{categoryLabel(selected.category)}</span>
            </div>

            {isSuperadmin && (
              <div className="form-group support-status-control">
                <label>Estado</label>
                <select className="form-select" value={selected.status} onChange={event => changeStatus(selected, event.target.value)}>
                  {STATUSES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </div>
            )}

            <div className="messages-list support-messages">
              {(selected.messages || []).map(message => {
                const isSupport = ['superadmin'].includes(message.sender_role)
                return (
                  <div key={message.id} className={`message-bubble ${isSupport ? 'message-outgoing' : 'message-incoming'}`}>
                    <div className="message-content">{message.message}</div>
                    <div className="message-meta">
                      {isSupport ? 'Soporte Turnix' : 'Negocio'} - {message.created_at ? new Date(message.created_at).toLocaleString('es-CO') : ''}
                    </div>
                  </div>
                )
              })}
            </div>

            {selected.status === 'closed' ? (
              <button type="button" className="btn btn-outline" onClick={() => reopenTicket(selected)}>Reabrir ticket</button>
            ) : (
              <form className="reply-form" onSubmit={handleReply}>
                <textarea
                  className="form-textarea reply-input"
                  rows={3}
                  value={reply}
                  onChange={event => setReply(event.target.value)}
                  placeholder="Escribe una respuesta..."
                />
                <div className="reply-actions">
                  <button type="button" className="btn btn-outline" onClick={() => closeTicket(selected)}>Cerrar ticket</button>
                  <button type="submit" className="btn btn-primary" disabled={sending || !reply.trim()}>
                    {sending ? 'Enviando...' : 'Responder'}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>

      {pagination.pages > 1 && (
        <div className="pagination-bar">
          <span>Total: {pagination.total} registros</span>
          <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage(current => current - 1)}>Anterior</button>
          <span>Página {pagination.page} de {pagination.pages}</span>
          <button className="btn btn-outline btn-sm" disabled={page >= pagination.pages} onClick={() => setPage(current => current + 1)}>Siguiente</button>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={event => event.target === event.currentTarget && setModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>Crear ticket</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            <form className="modal-form" onSubmit={handleCreate} noValidate>
              {isSuperadmin && (
                <div className="form-group">
                  <label>Negocio *</label>
                  <select className="form-select" name="tenant_id" value={form.tenant_id} onChange={handleFormChange}>
                    <option value="">Selecciona un negocio</option>
                    {businesses.map(business => <option key={business.id} value={business.id}>{business.name}</option>)}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>Asunto *</label>
                <input className="form-input" name="subject" value={form.subject} onChange={handleFormChange} placeholder="Ej: No puedo conectar el bot" />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Categoría</label>
                  <select className="form-select" name="category" value={form.category} onChange={handleFormChange}>
                    {CATEGORIES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Prioridad</label>
                  <select className="form-select" name="priority" value={form.priority} onChange={handleFormChange}>
                    {PRIORITIES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Descripción *</label>
                <textarea className="form-textarea" name="description" value={form.description} onChange={handleFormChange} rows={5} placeholder="Cuéntanos qué ocurrió y qué necesitas resolver." />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={saving || (isSuperadmin && !form.tenant_id)}>
                  {saving ? 'Enviando...' : 'Enviar ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
