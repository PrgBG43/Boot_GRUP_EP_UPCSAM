import { useEffect, useState } from 'react'
import api from '../api.js'
import { useAuth } from '../context/AuthContext.jsx'
import BusinessAccordion from '../components/BusinessAccordion.jsx'
import { groupByBusiness } from '../utils/businessGroups.js'
import { botStepLabel, channelLabel, statusBadgeClass, statusLabel } from '../utils/labels.js'
import { useRef } from 'react'

const asItems = data => data?.items || data || []

function capturePageScroll() {
  const container = document.querySelector('.main-content-wrapper')
  return {
    container,
    top: container ? container.scrollTop : window.scrollY,
    path: window.location.pathname,
  }
}

function restorePageScroll(snapshot) {
  if (!snapshot) return
  requestAnimationFrame(() => {
    if (window.location.pathname !== snapshot.path) return
    if (snapshot.container && document.body.contains(snapshot.container)) {
      snapshot.container.scrollTop = snapshot.top
      return
    }
    window.scrollTo({ top: snapshot.top, left: window.scrollX, behavior: 'auto' })
  })
}

export default function Conversations() {
  const { isSuperadmin, activeTenantId } = useAuth()
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
  const [replyText,     setReplyText]     = useState('')
  const [sending,       setSending]       = useState(false)
  const [messageError,  setMessageError]  = useState(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [hasNewMessages, setHasNewMessages] = useState(false)
  const messagesListRef = useRef(null)
  const messagesRef = useRef([])
  const scrollMessagesToEndRef = useRef(false)

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  const isMessagesNearBottom = () => {
    const el = messagesListRef.current
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80
  }

  const load = ({ preserveScroll = true } = {}) => {
    const scrollSnapshot = preserveScroll ? capturePageScroll() : null
    const params = { page, page_size: 20 }
    if (debouncedSearch) params.search = debouncedSearch
    if (status) params.status = status
    if (isSuperadmin && activeTenantId) params.tenant_id = activeTenantId
    api.getConversations(params)
      .then(c => {
        const items = asItems(c)
        setConversations(items)
        setSelected(current => {
          if (!current) return current
          return items.find(item => item.id === current.id) || current
        })
        setPagination(c?.items ? c : { total: (c || []).length, page: 1, page_size: (c || []).length, pages: 1 })
        setLastUpdated(new Date())
        setLoading(false)
        restorePageScroll(scrollSnapshot)
      })
      .catch(e => {
        setError(e.message)
        setLoading(false)
        restorePageScroll(scrollSnapshot)
      })
  }

  useEffect(() => {
    load({ preserveScroll: false })
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [status, page, activeTenantId, debouncedSearch])
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1)
      setDebouncedSearch(search.trim())
    }, 350)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    setPage(1)
    setSelected(null)
    setMessages([])
    setReplyText('')
    setMessageError(null)
    setHasNewMessages(false)
  }, [activeTenantId])

  const loadMessages = async (conv, { silent = false, scrollToEnd = false } = {}) => {
    if (!conv) return
    if (!silent) setLoadingMsgs(true)
    try {
      const previousLastId = messagesRef.current[messagesRef.current.length - 1]?.id
      const wasNearBottom = isMessagesNearBottom()
      const msgs = await api.getMessages(conv.id)
      const nextLastId = (msgs || [])[(msgs || []).length - 1]?.id
      if (scrollToEnd || !silent || (silent && wasNearBottom && previousLastId && nextLastId !== previousLastId)) {
        scrollMessagesToEndRef.current = true
      } else if (silent && previousLastId && nextLastId && nextLastId !== previousLastId) {
        setHasNewMessages(true)
      }
      setMessages(msgs || [])
    } catch(e) {
      if (!silent) {
        setMessages([])
        setMessageError(e.message || 'No fue posible cargar los mensajes de la conversación.')
      }
    }
    if (!silent) setLoadingMsgs(false)
  }

  const openConversation = async (conv) => {
    setSelected(conv)
    setReplyText('')
    setMessageError(null)
    setHasNewMessages(false)
    await loadMessages(conv, { scrollToEnd: true })
  }

  useEffect(() => {
    if (!selected) return undefined
    const timer = setInterval(() => loadMessages(selected, { silent: true }), 3000)
    return () => clearInterval(timer)
  }, [selected]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!scrollMessagesToEndRef.current || !messagesListRef.current) return
    messagesListRef.current.scrollTop = messagesListRef.current.scrollHeight
    scrollMessagesToEndRef.current = false
    setHasNewMessages(false)
  }, [messages])

  const handleSendMessage = async (event) => {
    event.preventDefault()
    const content = replyText.trim()
    if (!selected || !content) return
    setSending(true)
    setMessageError(null)
    try {
      const sent = await api.sendConversationMessage(selected.id, content)
      scrollMessagesToEndRef.current = true
      setMessages(prev => [...prev, sent])
      setReplyText('')
      load()
    } catch (e) {
      setMessageError(e.message || 'No fue posible enviar el mensaje.')
    }
    setSending(false)
  }

  const groupedConversations = isSuperadmin && !activeTenantId ? groupByBusiness(conversations) : []

  const renderConversationsTable = (items, showBusinessColumn = isSuperadmin && !!activeTenantId) => (
    <div className="table-responsive">
      <table className="data-table conversations-table">
        <thead>
          <tr>
            <th>ID</th>
            {showBusinessColumn && <th>Negocio</th>}
            <th>Cliente</th>
            <th>Canal</th>
            <th>Estado</th>
            <th>Paso</th>
            <th>Última interacción</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map(c => (
            <tr key={c.id} className="clickable-row" onClick={() => openConversation(c)}>
              <td className="cell-nowrap">#{c.id}</td>
              {showBusinessColumn && <td className="cell-nowrap">{c.tenant_name || 'Negocio sin nombre'}</td>}
              <td className="cell-nowrap">{c.client_name || `Chat ${c.chat_id}`}</td>
              <td className="cell-nowrap">{channelLabel(c.channel)}</td>
              <td><span className={`badge ${statusBadgeClass(c.status)}`}>{statusLabel(c.status)}</span></td>
              <td className="cell-nowrap">{botStepLabel(c.current_step)}</td>
              <td className="cell-nowrap">{c.last_interaction_at ? new Date(c.last_interaction_at).toLocaleString('es-CO') : '-'}</td>
              <td className="cell-actions">
                <div className="table-actions">
                  <button className="btn btn-outline btn-sm" onClick={(e) => { e.stopPropagation(); openConversation(c) }}>Ver mensajes</button>
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
          <h1>Conversaciones</h1>
          <p>{isSuperadmin && !activeTenantId ? 'Conversaciones agrupadas por negocio' : 'Historial bidireccional de conversaciones de Telegram'}</p>
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
          ) : isSuperadmin && !activeTenantId ? (
            <BusinessAccordion
              groups={groupedConversations}
              itemLabel={{ singular: 'conversación', plural: 'conversaciones' }}
              emptyTitle="Sin conversaciones registradas"
              emptyText="Las conversaciones aparecerán aquí cuando los clientes interactúen por Telegram."
              renderGroup={group => renderConversationsTable(group.items, false)}
            />
          ) : (
            renderConversationsTable(conversations, isSuperadmin)
          )}
        </div>

        {selected && (
          <div className="card">
            <div className="card-header-row">
              <div>
                <h3>Mensajes - Conversación #{selected.id}</h3>
                <span className="chat-subtitle">{selected.client_name || `Chat ${selected.chat_id}`}</span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setSelected(null)}>Cerrar</button>
            </div>
            {messageError && <div className="alert alert-error alert-compact">{messageError}</div>}
            {loadingMsgs ? <div className="spinner" /> : (
              messages.length === 0 ? (
                <div className="empty-state">
                  <h2 className="empty-state-title">Sin mensajes registrados</h2>
                  <p className="empty-state-text">Esta conversación todavía no tiene mensajes guardados.</p>
                </div>
              ) : (
                <div className="messages-list" ref={messagesListRef}>
                  {hasNewMessages && (
                    <button
                      type="button"
                      className="new-messages-indicator"
                      onClick={() => {
                        if (messagesListRef.current) {
                          messagesListRef.current.scrollTop = messagesListRef.current.scrollHeight
                        }
                        setHasNewMessages(false)
                      }}
                    >
                      Nuevos mensajes
                    </button>
                  )}
                  {messages.map(m => (
                    <div key={m.id} className={`message-bubble message-${m.direction}`}>
                      <div className="message-content">{m.content}</div>
                      <div className="message-meta">
                        {m.direction === 'incoming' ? 'Cliente' : 'Negocio'} - {m.created_at ? new Date(m.created_at).toLocaleTimeString('es-CO') : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
            <form className="reply-form" onSubmit={handleSendMessage}>
              <textarea
                className="form-textarea reply-input"
                value={replyText}
                onChange={e => setReplyText(e.target.value)}
                rows={3}
                placeholder="Escribe una respuesta para el cliente..."
              />
              <div className="reply-actions">
                <span className="reply-hint">Se enviará por el bot de Telegram conectado al negocio.</span>
                <button className="btn btn-primary" type="submit" disabled={sending || !replyText.trim()}>
                  {sending ? 'Enviando...' : 'Enviar'}
                </button>
              </div>
            </form>
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

