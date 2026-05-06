import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

export default function BusinessConfig() {
  const { isSuperadmin } = useAuth()
  const navigate = useNavigate()
  const [business, setBusiness] = useState(null)
  const [form,     setForm]     = useState({})
  const [loading,  setLoading]  = useState(true)
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState(null)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    if (isSuperadmin) { navigate('/admin/tenants', { replace: true }); return }
    api.getMyBusiness()
      .then(b => { setBusiness(b); setForm(toForm(b)); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [isSuperadmin])

  const toForm = b => ({
    name:         b?.name         || '',
    description:  b?.description  || '',
    phone:        b?.phone        || '',
    address:      b?.address      || '',
    opening_time: b?.opening_time || '08:00',
    closing_time: b?.closing_time || '20:00',
  })

  const handleChange = e => {
    const { name, value } = e.target
    setForm(f => ({ ...f, [name]: value }))
  }

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      await api.updateBusiness(business.id, form)
      setFeedback({ type: 'success', msg: 'Datos actualizados correctamente.' })
    } catch(err) {
      setFeedback({ type: 'error', msg: err.message })
    }
    setSaving(false)
  }

  if (isSuperadmin) return null
  if (loading)      return <div className="spinner" />
  if (error)        return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Mi Negocio</h1>
          <p>Actualiza los datos y horarios de tu negocio</p>
        </div>
        {business && (
          <span className={`badge ${business.is_active ? 'badge-confirmed' : 'badge-cancelled'}`}>
            {business.is_active ? 'Activo' : 'Inactivo'}
          </span>
        )}
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`} style={{marginBottom:'1.25rem'}}>
          {feedback.msg}
        </div>
      )}

      {business && (
        <div className="card" style={{maxWidth:'680px'}}>
          <div style={{marginBottom:'1.5rem',fontSize:'.85rem',color:'var(--text-muted)'}}>
            Slug: <code>{business.slug}</code>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Nombre del negocio *</label>
              <input name="name" value={form.name} onChange={handleChange} required />
            </div>
            <div className="form-group">
              <label>Descripcion</label>
              <textarea name="description" value={form.description} onChange={handleChange} rows={3} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Telefono</label>
                <input name="phone" value={form.phone} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Direccion</label>
                <input name="address" value={form.address} onChange={handleChange} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Hora apertura</label>
                <input type="time" name="opening_time" value={form.opening_time} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Hora cierre</label>
                <input type="time" name="closing_time" value={form.closing_time} onChange={handleChange} />
              </div>
            </div>
            <div style={{display:'flex',justifyContent:'flex-end',marginTop:'1rem'}}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Guardando...' : 'Guardar cambios'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}