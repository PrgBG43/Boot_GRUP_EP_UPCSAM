import { useEffect, useState } from 'react'
import api from '../api.js'

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', password: '', phone: '',
}

export default function Staff() {
  const [staff,    setStaff]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [modal,    setModal]    = useState(false)
  const [form,     setForm]     = useState(EMPTY_FORM)
  const [saving,   setSaving]   = useState(false)
  const [feedback, setFeedback] = useState(null)

  const load = () => {
    setLoading(true)
    api.getStaff()
      .then(s => { setStaff(s || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [])

  const openCreate = () => { setForm(EMPTY_FORM); setModal(true); setFeedback(null) }

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      await api.createStaff({
        first_name: form.first_name,
        last_name:  form.last_name,
        email:      form.email,
        password:   form.password,
        phone:      form.phone || undefined,
        role_name:  'staff',
      })
      setModal(false); load()
    } catch(e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const toggleActive = async (s) => {
    const action = s.is_active ? api.deactivateStaff : api.activateStaff
    try { await action(s.id); load() } catch(e) { alert(e.message) }
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Personal</h1>
          <p>Gestiona el equipo de trabajo de tu negocio</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Agregar miembro</button>
      </div>

      <div className="card">
        {staff.length === 0 ? (
          <div className="empty-state">
            <div className="icon">👤</div>
            <p>No hay personal registrado aún.</p>
            <button className="btn btn-primary" onClick={openCreate}>Agregar primer miembro</button>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {staff.map(s => (
                <tr key={s.id}>
                  <td>
                    <strong>{s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim()}</strong>
                    {s.phone && <div className="table-sub">📞 {s.phone}</div>}
                  </td>
                  <td className="table-sub">{s.email}</td>
                  <td>
                    <span className={`badge ${s.is_active ? 'badge-confirmed' : 'badge-cancelled'}`}>
                      {s.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td>
                    <div className="table-actions">
                      <button
                        className={`btn-sm ${s.is_active ? 'btn-danger-sm' : 'btn-success-sm'}`}
                        onClick={() => toggleActive(s)}
                      >
                        {s.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
                  </td>
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
              <h3>Agregar miembro del personal</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type}`} style={{margin:'0 1.5rem'}}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input name="first_name" value={form.first_name} onChange={handleChange} required placeholder="Nombre" />
                </div>
                <div className="form-group">
                  <label>Apellido *</label>
                  <input name="last_name" value={form.last_name} onChange={handleChange} required placeholder="Apellido" />
                </div>
              </div>
              <div className="form-group">
                <label>Correo electrónico *</label>
                <input type="email" name="email" value={form.email} onChange={handleChange} required placeholder="correo@ejemplo.com" />
              </div>
              <div className="form-group">
                <label>Contraseña *</label>
                <input type="password" name="password" value={form.password} onChange={handleChange} required minLength={8} placeholder="Mínimo 8 caracteres" />
              </div>
              <div className="form-group">
                <label>Teléfono</label>
                <input name="phone" value={form.phone} onChange={handleChange} placeholder="+57 300 000 0000" />
              </div>
            </form>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={() => setModal(false)}>Cancelar</button>
              <button type="button" className="btn btn-primary" disabled={saving} onClick={handleSubmit}>
                {saving ? 'Guardando...' : 'Crear cuenta'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
