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
    } catch(e) { setMessages([]) }
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

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
        <div className="card">
          {conversations.length === 0 ? (
            <div className="empty-state"><div className="icon">💬</div><p>No hay conversaciones registradas.</p></div>
          ) : (
            <table>
              <thead><tr><th>ID</th><th>Chat ID</th><th>Canal</th><th>Estado</th><th>Visitas</th><th>Última interacción</th><th></th></tr></thead>
              <tbody>
                {conversations.map(c => (
                  <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => openConversation(c)}>
                    <td>#{c.id}</td>
                    <td>{c.chat_id}</td>
                    <td>{c.channel}</td>
                    <td><span className={`badge badge-${c.status === 'active' ? 'active' : 'inactive'}`}>{c.status}</span></td>
                    <td>{c.visit_count}</td>
                    <td>{c.last_interaction_at ? new Date(c.last_interaction_at).toLocaleString('es-CO') : '—'}</td>
                    <td><button className="btn-ghost btn-sm">Ver mensajes</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {selected && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3>Mensajes – Conversación #{selected.id}</h3>
              <button className="btn-ghost btn-sm" onClick={() => setSelected(null)}>Cerrar ×</button>
            </div>
            {loadingMsgs ? <div className="spinner" /> : (
              messages.length === 0 ? (
                <div className="empty-state"><div className="icon">💬</div><p>Sin mensajes registrados.</p></div>
              ) : (
                <div className="messages-list">
                  {messages.map(m => (
                    <div key={m.id} className={`message-bubble message-${m.direction}`}>
                      <div className="message-content">{m.content}</div>
                      <div className="message-meta">
                        {m.direction === 'incoming' ? '👤 Cliente' : '🤖 Bot'} · {m.created_at ? new Date(m.created_at).toLocaleTimeString('es-CO') : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        )}
      </div>

      <style>{`
        .messages-list { display: flex; flex-direction: column; gap: .75rem; max-height: 500px; overflow-y: auto; }
        .message-bubble { max-width: 85%; padding: .6rem .9rem; border-radius: 12px; }
        .message-incoming { align-self: flex-start; background: #f3f4f6; }
        .message-outgoing { align-self: flex-end; background: #ede9fe; }
        .message-content { font-size: .9rem; }
        .message-meta { font-size: .72rem; color: var(--text-muted); margin-top: .25rem; }
      `}</style>
    </div>
  )
}
