import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

function FieldError({ msg }) {
  if (!msg) return null
  return <span className="field-error">{msg}</span>
}

function validatePhone(phone) {
  if (!phone || !phone.trim()) return 'El teléfono debe tener 10 dígitos y comenzar por 3.'
  if (!/^3[0-9]{9}$/.test(phone.trim())) return 'El teléfono debe tener 10 dígitos y comenzar por 3.'
  return null
}

const EMPTY_FORM = {
  first_name: '', last_name: '', email: '', password: '', confirm_password: '', phone: '',
}

export default function Staff() {
  const { isSuperadmin, activeTenantId } = useAuth()
  const [staff,    setStaff]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [modal,    setModal]    = useState(false)
  const [form,     setForm]     = useState(EMPTY_FORM)
  const [saving,   setSaving]   = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})

  const load = () => {
    setLoading(true)
    api.getStaff(activeTenantId || undefined)
      .then(s => { setStaff(s || []); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(load, [activeTenantId])

  const openCreate = () => { setForm(EMPTY_FORM); setModal(true); setFeedback(null); setFieldErrors({}) }

  const handleChange = e => {
    const { name, value } = e.target
    const nextValue = name === 'phone' ? value.replace(/\D/g, '').slice(0, 10) : value
    setForm(f => ({ ...f, [name]: nextValue }))
    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: null }))
    }
  }

  const validate = () => {
    const errs = {}
    if (!form.first_name.trim()) errs.first_name = 'El nombre es obligatorio.'
    if (!form.last_name.trim())  errs.last_name  = 'El apellido es obligatorio.'
    if (!form.email.trim())      errs.email      = 'El correo electrónico es obligatorio.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      errs.email = 'Ingresa un correo electrónico válido.'
    if (!form.password)          errs.password   = 'La contraseña es obligatoria.'
    else if (form.password.length < 8)
      errs.password = 'La contraseña debe tener al menos 8 caracteres.'
    if (!form.confirm_password)
      errs.confirm_password = 'Confirma la contraseña.'
    else if (form.password !== form.confirm_password)
      errs.confirm_password = 'Las contraseñas no coinciden.'
    const phoneError = validatePhone(form.phone)
    if (phoneError) errs.phone = phoneError
    return errs
  }

  const handleSubmit = async e => {
    e.preventDefault(); setFeedback(null)
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs)
      setFeedback({ type: 'error', msg: 'Corrige los errores del formulario antes de continuar.' })
      return
    }
    setSaving(true)
    try {
      await api.createStaff({
        first_name: form.first_name.trim(),
        last_name:  form.last_name.trim(),
        email:      form.email.trim(),
        password:   form.password,
        phone:      form.phone.trim() || undefined,
        role_name:  'staff',
        tenant_id:  activeTenantId || undefined,
      })
      setModal(false); load()
    } catch(e) {
      if ((e.message || '').toLowerCase().includes('correo')) {
        setFieldErrors(prev => ({ ...prev, email: 'El correo ya está registrado.' }))
      }
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const toggleActive = async (s) => {
    const action = s.is_active ? api.deactivateUser : api.activateUser
    try { await action(s.id); load() } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
  }

  const deleteStaff = async (s) => {
    const typed = window.prompt('Esta acción eliminará definitivamente el usuario y no se podrá recuperar. Escribe ELIMINAR para continuar.')
    if (typed !== 'ELIMINAR') return
    try { await api.deleteUser(s.id); load() } catch(e) { setFeedback({ type: 'error', msg: e.message }) }
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

      <div className="table-card">
        {staff.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state-title">Sin personal registrado</h2>
            <p className="empty-state-text">Agrega miembros del equipo para administrar disponibilidad y atención.</p>
            <button className="btn btn-primary empty-state-action" onClick={openCreate}>Agregar primer miembro</button>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table staff-table">
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
                    <span className="cell-main">{s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim()}</span>
                    {s.phone && <span className="cell-muted">Teléfono: {s.phone}</span>}
                  </td>
                  <td><span className="cell-email">{s.email}</span></td>
                  <td>
                    <span className={`badge ${s.is_active ? 'badge-success' : 'badge-neutral'}`}>
                      {s.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="cell-actions">
                    <div className="table-actions">
                      <button
                        className={`btn btn-sm ${s.is_active ? 'btn-danger' : 'btn-success'}`}
                        onClick={() => toggleActive(s)}
                      >
                        {s.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                      {isSuperadmin && (
                        <button className="btn btn-outline btn-sm" onClick={() => deleteStaff(s)}>
                          Eliminar definitivamente
                        </button>
                      )}
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
              <h3>Agregar miembro del personal</h3>
              <button className="modal-close" onClick={() => setModal(false)}>×</button>
            </div>
            {feedback && <div className={`alert alert-${feedback.type} modal-alert`}>{feedback.msg}</div>}
            <form onSubmit={handleSubmit} className="modal-form" noValidate>
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input
                    name="first_name" value={form.first_name} onChange={handleChange}
                    placeholder="Nombre"
                    className={fieldErrors.first_name ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.first_name} />
                </div>
                <div className="form-group">
                  <label>Apellido *</label>
                  <input
                    name="last_name" value={form.last_name} onChange={handleChange}
                    placeholder="Apellido"
                    className={fieldErrors.last_name ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.last_name} />
                </div>
              </div>
              <div className="form-group">
                <label>Correo electrónico *</label>
                <input
                  type="email" name="email" value={form.email} onChange={handleChange}
                  placeholder="correo@ejemplo.com"
                  className={fieldErrors.email ? 'input-error' : ''}
                />
                <FieldError msg={fieldErrors.email} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Contraseña *</label>
                  <input
                    type="password" name="password" value={form.password} onChange={handleChange}
                    placeholder="Mínimo 8 caracteres"
                    className={fieldErrors.password ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.password} />
                </div>
                <div className="form-group">
                  <label>Confirmar contraseña *</label>
                  <input
                    type="password" name="confirm_password" value={form.confirm_password} onChange={handleChange}
                    placeholder="Repetir contraseña"
                    className={fieldErrors.confirm_password ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.confirm_password} />
                </div>
              </div>
              <div className="form-group">
                <label>Teléfono *</label>
                <input
                  name="phone"
                  value={form.phone}
                  onChange={handleChange}
                  placeholder="3001234567"
                  inputMode="numeric"
                  maxLength={10}
                  className={fieldErrors.phone ? 'input-error' : ''}
                />
                <FieldError msg={fieldErrors.phone} />
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
