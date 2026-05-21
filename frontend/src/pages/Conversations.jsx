import { useEffect, useState } from 'react'
import api from '../api.js'

export default function Conversations() {
  const [conversations, setConversations] = useState([])
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState(null)
  const [selected,      setSelected]      = useState(null)
  const [messages,      setMessages]      = useState([])
  const [loadingMsgs,   setLoadingMsgs]   = useState(false)

  useEffect(() => {
    api.getConversations()
      .then(c => { setConversations(c || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

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
        <h1>Conversaciones</h1>
        <p>Registro de conversaciones de Telegram</p>
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
              <thead><tr><th>ID</th><th>Chat ID</th><th>Canal</th><th>Estado</th><th>Visitas</th><th>Última interacción</th><th>Acciones</th></tr></thead>
              <tbody>
                {conversations.map(c => (
                  <tr key={c.id} className="clickable-row" onClick={() => openConversation(c)}>
                    <td className="cell-nowrap">#{c.id}</td>
                    <td className="cell-nowrap">{c.chat_id}</td>
                    <td className="cell-nowrap">{c.channel}</td>
                    <td><span className={`badge ${c.status === 'active' ? 'badge-success' : 'badge-neutral'}`}>{c.status}</span></td>
                    <td className="cell-nowrap">{c.visit_count}</td>
                    <td className="cell-nowrap">{c.last_interaction_at ? new Date(c.last_interaction_at).toLocaleString('es-CO') : '—'}</td>
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
              <h3>Mensajes – Conversación #{selected.id}</h3>
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
                        {m.direction === 'incoming' ? 'Cliente' : 'Bot'} · {m.created_at ? new Date(m.created_at).toLocaleTimeString('es-CO') : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  )
}
