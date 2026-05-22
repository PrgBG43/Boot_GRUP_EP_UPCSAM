import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const DAY_LABELS = [
  ['0', 'Lunes'],
  ['1', 'Martes'],
  ['2', 'Miércoles'],
  ['3', 'Jueves'],
  ['4', 'Viernes'],
  ['5', 'Sábado'],
  ['6', 'Domingo'],
]

const DEFAULT_SCHEDULE = {
  0: { active: true, open: '08:00', close: '18:00', break_start: '', break_end: '' },
  1: { active: true, open: '08:00', close: '18:00', break_start: '', break_end: '' },
  2: { active: true, open: '08:00', close: '18:00', break_start: '', break_end: '' },
  3: { active: true, open: '08:00', close: '18:00', break_start: '', break_end: '' },
  4: { active: true, open: '08:00', close: '18:00', break_start: '', break_end: '' },
  5: { active: true, open: '08:00', close: '16:00', break_start: '', break_end: '' },
  6: { active: false, open: '08:00', close: '16:00', break_start: '', break_end: '' },
}

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
    weekly_schedule: { ...DEFAULT_SCHEDULE, ...(b?.weekly_schedule || {}) },
    base_slot_minutes: b?.base_slot_minutes || 30,
    min_booking_notice_minutes: b?.min_booking_notice_minutes ?? 30,
    max_booking_days: b?.max_booking_days || 30,
    blocked_dates: b?.blocked_dates || [],
    blocked_time_ranges: b?.blocked_time_ranges || [],
  })

  const handleChange = e => {
    const { name, value } = e.target
    setForm(f => ({ ...f, [name]: value }))
  }

  const handleScheduleChange = (day, field, value) => {
    setForm(f => ({
      ...f,
      weekly_schedule: {
        ...f.weekly_schedule,
        [day]: {
          ...(f.weekly_schedule?.[day] || DEFAULT_SCHEDULE[day]),
          [field]: field === 'active' ? value === true : value,
        },
      },
    }))
  }

  const addBlockedDate = () => {
    setForm(f => ({ ...f, blocked_dates: [...(f.blocked_dates || []), { date: '', reason: '' }] }))
  }

  const updateBlockedDate = (index, field, value) => {
    setForm(f => ({
      ...f,
      blocked_dates: (f.blocked_dates || []).map((item, i) => i === index ? { ...item, [field]: value } : item),
    }))
  }

  const removeBlockedDate = index => {
    setForm(f => ({ ...f, blocked_dates: (f.blocked_dates || []).filter((_, i) => i !== index) }))
  }

  const addBlockedRange = () => {
    setForm(f => ({ ...f, blocked_time_ranges: [...(f.blocked_time_ranges || []), { date: '', start: '12:00', end: '14:00', reason: '' }] }))
  }

  const updateBlockedRange = (index, field, value) => {
    setForm(f => ({
      ...f,
      blocked_time_ranges: (f.blocked_time_ranges || []).map((item, i) => i === index ? { ...item, [field]: value } : item),
    }))
  }

  const removeBlockedRange = index => {
    setForm(f => ({ ...f, blocked_time_ranges: (f.blocked_time_ranges || []).filter((_, i) => i !== index) }))
  }

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      const payload = {
        ...form,
        base_slot_minutes: Number(form.base_slot_minutes),
        min_booking_notice_minutes: Number(form.min_booking_notice_minutes),
        max_booking_days: Number(form.max_booking_days),
        blocked_dates: (form.blocked_dates || []).filter(item => item.date),
        blocked_time_ranges: (form.blocked_time_ranges || []).filter(item => item.date && item.start && item.end),
      }
      await api.updateBusiness(business.id, payload)
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
          <span className={`badge ${business.is_active ? 'badge-success' : 'badge-neutral'}`}>
            {business.is_active ? 'Activo' : 'Inactivo'}
          </span>
        )}
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`}>
          {feedback.msg}
        </div>
      )}

      {business && (
        <div className="card business-config-card">
          <div className="panel-meta business-slug">
            Slug: <code>{business.slug}</code>
          </div>
          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label>Nombre del negocio *</label>
              <input name="name" value={form.name} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Descripción</label>
              <textarea name="description" value={form.description} onChange={handleChange} rows={3} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Teléfono</label>
                <input name="phone" value={form.phone} onChange={handleChange} />
              </div>
              <div className="form-group">
                <label>Dirección</label>
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
            <div className="modal-section-header modal-section-header-spaced">Disponibilidad / Agenda del negocio</div>
            <div className="form-row">
              <div className="form-group">
                <label>Duración base de turnos</label>
                <select name="base_slot_minutes" value={form.base_slot_minutes} onChange={handleChange}>
                  <option value="15">15 minutos</option>
                  <option value="30">30 minutos</option>
                  <option value="45">45 minutos</option>
                  <option value="60">60 minutos</option>
                </select>
              </div>
              <div className="form-group">
                <label>Anticipación mínima</label>
                <select name="min_booking_notice_minutes" value={form.min_booking_notice_minutes} onChange={handleChange}>
                  <option value="0">Sin espera mínima</option>
                  <option value="30">30 minutos</option>
                  <option value="60">1 hora</option>
                  <option value="120">2 horas</option>
                </select>
              </div>
              <div className="form-group">
                <label>Agenda disponible hacia adelante</label>
                <select name="max_booking_days" value={form.max_booking_days} onChange={handleChange}>
                  <option value="7">7 días</option>
                  <option value="30">30 días</option>
                  <option value="90">90 días</option>
                  <option value="365">Todo el año</option>
                </select>
                {business?.plan?.name === 'free' && <small className="form-help">El plan Gratuito permite ofrecer hasta 7 días hacia adelante.</small>}
              </div>
            </div>

            <div className="table-responsive section-spacing">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Día</th>
                    <th>Activo</th>
                    <th>Apertura</th>
                    <th>Cierre</th>
                    <th>Pausa inicio</th>
                    <th>Pausa fin</th>
                  </tr>
                </thead>
                <tbody>
                  {DAY_LABELS.map(([day, label]) => {
                    const item = form.weekly_schedule?.[day] || DEFAULT_SCHEDULE[day]
                    return (
                      <tr key={day}>
                        <td className="cell-nowrap">{label}</td>
                        <td>
                          <input type="checkbox" checked={!!item.active} onChange={e => handleScheduleChange(day, 'active', e.target.checked)} />
                        </td>
                        <td><input type="time" value={item.open || '08:00'} onChange={e => handleScheduleChange(day, 'open', e.target.value)} disabled={!item.active} /></td>
                        <td><input type="time" value={item.close || '18:00'} onChange={e => handleScheduleChange(day, 'close', e.target.value)} disabled={!item.active} /></td>
                        <td><input type="time" value={item.break_start || ''} onChange={e => handleScheduleChange(day, 'break_start', e.target.value)} disabled={!item.active} /></td>
                        <td><input type="time" value={item.break_end || ''} onChange={e => handleScheduleChange(day, 'break_end', e.target.value)} disabled={!item.active} /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="surface-grid surface-grid--split section-spacing">
              <div className="availability-panel">
                <div className="card-header-row">
                  <h3>Fechas bloqueadas</h3>
                  <button type="button" className="btn btn-outline btn-sm" onClick={addBlockedDate}>Agregar fecha</button>
                </div>
                {(form.blocked_dates || []).length === 0 ? <div className="empty-state-sm">Sin fechas bloqueadas</div> : (
                  <div className="stack-sm">
                    {form.blocked_dates.map((item, index) => (
                      <div className="form-row" key={index}>
                        <input type="date" value={item.date || ''} onChange={e => updateBlockedDate(index, 'date', e.target.value)} />
                        <input placeholder="Motivo" value={item.reason || ''} onChange={e => updateBlockedDate(index, 'reason', e.target.value)} />
                        <button type="button" className="btn btn-outline btn-sm" onClick={() => removeBlockedDate(index)}>Quitar</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="availability-panel">
                <div className="card-header-row">
                  <h3>Horarios bloqueados</h3>
                  <button type="button" className="btn btn-outline btn-sm" onClick={addBlockedRange}>Agregar franja</button>
                </div>
                {(form.blocked_time_ranges || []).length === 0 ? <div className="empty-state-sm">Sin franjas bloqueadas</div> : (
                  <div className="stack-sm">
                    {form.blocked_time_ranges.map((item, index) => (
                      <div className="form-row" key={index}>
                        <input type="date" value={item.date || ''} onChange={e => updateBlockedRange(index, 'date', e.target.value)} />
                        <input type="time" value={item.start || ''} onChange={e => updateBlockedRange(index, 'start', e.target.value)} />
                        <input type="time" value={item.end || ''} onChange={e => updateBlockedRange(index, 'end', e.target.value)} />
                        <button type="button" className="btn btn-outline btn-sm" onClick={() => removeBlockedRange(index)}>Quitar</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="form-actions">
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
