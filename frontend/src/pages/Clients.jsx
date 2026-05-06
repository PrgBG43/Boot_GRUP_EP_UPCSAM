import { useEffect, useState } from 'react'
import api from '../api.js'

export default function Clients() {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [modal,   setModal]   = useState(false)
  const [form,    setForm]    = useState({ full_name: '', username: '', phone: '', telegram_user_id: '' })
  const [editing, setEditing] = useState(null)
  const [saving,  setSaving]  = useState(false)
  const [feedback,setFeedback]= useState(null)
  const [search,  setSearch]  = useState('')

  const load = () => {
    setLoading(true)
    api.getClients()
      .then(c => { setClients(c || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [])

  const filtered = clients.filter(c =>
    c.full_name.toLowerCase().includes(search.toLowerCase()) ||
    (c.username || '').toLowerCase().includes(search.toLowerCase()) ||
    (c.phone || '').includes(search)
  )

  const openCreate = () => { setForm({ full_name: '', username: '', phone: '', telegram_user_id: '' }); setEditing(null); setModal(true); setFeedback(null) }
  const openEdit   = c  => { setForm({ full_name: c.full_name, username: c.username || '', phone: c.phone || '', telegram_user_id: c.telegram_user_id || '' }); setEditing(c.id); setModal(true); setFeedback(null) }

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      if (editing) await api.updateClient(editing, form)
      else          await api.createClient(form)
      setModal(false); load()
    } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
    setSaving(false)
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <h1>Clientes</h1>
        <p>Clientes registrados en el sistema</p>
      </div>

      <div className="actions-bar">
        <div className="filters">
          <input placeholder="Buscar por nombre, usuario o teléfono…" value={search} onChange={e => setSearch(e.target.value)} style={{maxWidth:'300px'}} />
        </div>
        <button className="btn-primary" onClick={openCreate}>+ Nuevo cliente</button>
      </div>

      <div className="card">
        {filtered.length === 0 ? (
          <div className="empty-state"><div className="icon">👥</div><p>No hay clientes{search ? ' que coincidan.' : ' registrados.'}</p></div>
        ) : (
          <table>
            <thead><tr><th>ID</th><th>Nombre</th><th>Usuario Telegram</th><th>Teléfono</th><th>ID Telegram</th><th>Registrado</th><th>Acciones</th></tr></thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.id}>
                  <td>#{c.id}</td>
                  <td><strong>{c.full_name}</strong></td>
                  <td>{c.username ? `@${c.username}` : '—'}</td>
                  <td>{c.phone || '—'}</td>
                  <td>{c.telegram_user_id || '—'}</td>
                  <td>{c.created_at ? new Date(c.created_at).toLocaleDateString('es-CO') : '—'}</td>
                  <td><button className="btn-ghost btn-sm" onClick={() => openEdit(c)}>Editar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
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
            <form onSubmit={handleSubmit}>
              <div className="form-group"><label>Nombre completo *</label><input name="full_name" value={form.full_name} onChange={handleChange} required /></div>
              <div className="form-group"><label>Usuario de Telegram</label><input name="username" value={form.username} onChange={handleChange} placeholder="sin @" /></div>
              <div className="form-group"><label>Teléfono</label><input name="phone" value={form.phone} onChange={handleChange} /></div>
              <div className="form-group"><label>ID de Telegram</label><input name="telegram_user_id" value={form.telegram_user_id} onChange={handleChange} /></div>
              <div style={{display:'flex',gap:'.6rem',justifyContent:'flex-end',marginTop:'1rem'}}>
                <button type="button" className="btn-ghost" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Guardando...' : 'Guardar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
