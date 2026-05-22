import { useEffect, useState } from 'react'
import api from '../api.js'
import { botStepLabel, channelLabel, statusBadgeClass, statusLabel } from '../utils/labels.js'

const asItems = data => data?.items || data || []

export default function Conversations() {
  const [conversations, setConversations] = useState([])
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState(null)
  const [selected,      setSelected]      = useState(null)
  const [messages,      setMessages]      = useState([])
  const [loadingMsgs,   setLoadingMsgs]   = useState(false)
  const [search,        setSearch]        = useState('')
  const [status,        setStatus]        = useState('')
  const [page,          setPage]          = useState(1)
  const [pagination,    setPagination]    = useState({ total: 0, page: 1, page_size: 20, pages: 0 })
  const [lastUpdated,   setLastUpdated]   = useState(null)

  const load = () => {
    const params = { page, page_size: 20 }
    if (search.trim()) params.search = search.trim()
    if (status) params.status = status
    api.getConversations(params)
      .then(c => {
        setConversations(asItems(c))
        setPagination(c?.items ? c : { total: (c || []).length, page: 1, page_size: (c || []).length, pages: 1 })
        setLastUpdated(new Date())
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [status, page])
  useEffect(() => {
    const timer = setTimeout(() => { setPage(1); load() }, 350)
    return () => clearTimeout(timer)
  }, [search])  // eslint-disable-line react-hooks/exhaustive-deps

  const openConversation = async (conv) => {
    setSelected(conv)
    setLoadingMsgs(true)
    try {
      const msgs = await api.getMessages(conv.id)
      setMessages(msgs || [])
    } catch(e) {
      setMessages([])
      setError(e.message || 'No fue posible cargar los mensajes de la conversación.')
    }
    setLoadingMsgs(false)
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Conversaciones</h1>
          <p>Historial bidireccional de conversaciones de Telegram</p>
        </div>
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
        </div>
      </div>

      <div className="page-toolbar">
        <div className="filter-group">
          <input className="search-input" placeholder="Buscar cliente, chat o negocio..." value={search} onChange={e => setSearch(e.target.value)} />
          <select className="filter-select" value={status} onChange={e => { setPage(1); setStatus(e.target.value) }}>
            <option value="">Todos los estados</option>
            <option value="active">Activas</option>
            <option value="closed">Cerradas</option>
          </select>
        </div>
      </div>

      <div className={`section-spacing conversation-grid${selected ? ' conversation-grid--split' : ''}`}>
        <div className="table-card">
          {conversations.length === 0 ? (
            <div className="empty-state">
              <h2 className="empty-state-title">Sin conversaciones registradas</h2>
              <p className="empty-state-text">Las conversaciones aparecerán aquí cuando los clientes interactúen por Telegram.</p>
            </div>
          ) : (
            <div className="table-responsive">
            <table className="data-table conversations-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Negocio</th>
                  <th>Cliente</th>
                  <th>Canal</th>
                  <th>Estado</th>
                  <th>Paso</th>
                  <th>Última interacción</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {conversations.map(c => (
                  <tr key={c.id} className="clickable-row" onClick={() => openConversation(c)}>
                    <td className="cell-nowrap">#{c.id}</td>
                    <td className="cell-nowrap">{c.tenant_name || `#${c.tenant_id}`}</td>
                    <td className="cell-nowrap">{c.client_name || `Chat ${c.chat_id}`}</td>
                    <td className="cell-nowrap">{channelLabel(c.channel)}</td>
                    <td><span className={`badge ${statusBadgeClass(c.status)}`}>{statusLabel(c.status)}</span></td>
                    <td className="cell-nowrap">{botStepLabel(c.current_step)}</td>
                    <td className="cell-nowrap">{c.last_interaction_at ? new Date(c.last_interaction_at).toLocaleString('es-CO') : '-'}</td>
                    <td className="cell-actions">
                      <div className="table-actions">
                        <button className="btn btn-outline btn-sm">Ver mensajes</button>
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
          <div className="card">
            <div className="card-header-row">
              <h3>Mensajes - Conversación #{selected.id}</h3>
              <button className="btn btn-outline btn-sm" onClick={() => setSelected(null)}>Cerrar</button>
            </div>
            {loadingMsgs ? <div className="spinner" /> : (
              messages.length === 0 ? (
                <div className="empty-state">
                  <h2 className="empty-state-title">Sin mensajes registrados</h2>
                  <p className="empty-state-text">Esta conversación todavía no tiene mensajes guardados.</p>
                </div>
              ) : (
                <div className="messages-list">
                  {messages.map(m => (
                    <div key={m.id} className={`message-bubble message-${m.direction}`}>
                      <div className="message-content">{m.content}</div>
                      <div className="message-meta">
                        {m.direction === 'incoming' ? 'Cliente' : 'Bot'} - {m.created_at ? new Date(m.created_at).toLocaleTimeString('es-CO') : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
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
    </div>
  )
}

