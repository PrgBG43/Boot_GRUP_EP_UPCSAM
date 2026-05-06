import { useEffect, useState } from 'react'
import api from '../api.js'

const DEFAULT_MSGS = {
  welcome_message:   '¡Hola! Bienvenido a nuestro sistema de citas. ¿En qué podemos ayudarte?',
  services_message:  'Estos son nuestros servicios disponibles:',
  ask_date_message:  '¿Qué fecha prefieres para tu cita?',
  ask_time_message:  '¿A qué hora te gustaría?',
  confirm_message:   '¡Tu cita ha sido confirmada! Te esperamos.',
  cancel_message:    'Tu cita ha sido cancelada.',
}

export default function TelegramConfig() {
  const [config,   setConfig]   = useState(null)
  const [form,     setForm]     = useState({})
  const [loading,  setLoading]  = useState(true)
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState(null)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    api.getTelegramConfig()
      .then(c => { setConfig(c); setForm(c); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async e => {
    e.preventDefault(); setSaving(true); setFeedback(null)
    try {
      const updated = await api.updateTelegramConfig(form)
      setConfig(updated); setForm(updated)
      setFeedback({ type: 'success', msg: '¡Configuración guardada correctamente!' })
    } catch(e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  if (loading) return <div className="spinner" />
  if (error)   return <div className="alert alert-error">Error: {error}</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Configuración de Telegram</h1>
          <p>Personaliza los mensajes del bot de Telegram para tu negocio</p>
        </div>
      </div>

      {feedback && (
        <div className={`alert alert-${feedback.type}`} style={{marginBottom:'1.25rem'}}>
          {feedback.msg}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1.5rem'}}>

          {/* Columna: mensajes */}
          <div className="card">
            <h3 style={{marginTop:0,marginBottom:'1.25rem',fontSize:'1rem'}}>💬 Mensajes del bot</h3>

            {[
              { key: 'welcome_message',   label: 'Mensaje de bienvenida',   ph: DEFAULT_MSGS.welcome_message },
              { key: 'services_message',  label: 'Texto antes de servicios', ph: DEFAULT_MSGS.services_message },
              { key: 'ask_date_message',  label: 'Pregunta por fecha',       ph: DEFAULT_MSGS.ask_date_message },
              { key: 'ask_time_message',  label: 'Pregunta por hora',        ph: DEFAULT_MSGS.ask_time_message },
              { key: 'confirm_message',   label: 'Confirmación de cita',     ph: DEFAULT_MSGS.confirm_message },
              { key: 'cancel_message',    label: 'Cancelación de cita',      ph: DEFAULT_MSGS.cancel_message },
            ].map(({ key, label, ph }) => (
              <div className="form-group" key={key}>
                <label>{label}</label>
                <textarea
                  name={key}
                  value={form[key] || ''}
                  onChange={handleChange}
                  rows={2}
                  placeholder={ph}
                />
              </div>
            ))}
          </div>

          {/* Columna: opciones */}
          <div>
            <div className="card" style={{marginBottom:'1rem'}}>
              <h3 style={{marginTop:0,marginBottom:'1.25rem',fontSize:'1rem'}}>⚙️ Opciones del bot</h3>

              <div className="form-group form-check">
                <input type="checkbox" id="allow_cancellation" name="allow_cancellation"
                  checked={!!form.allow_cancellation} onChange={handleChange} />
                <label htmlFor="allow_cancellation">
                  <strong>Permitir cancelaciones</strong>
                  <div style={{fontSize:'.8rem',color:'var(--text-muted)'}}>Los clientes pueden cancelar citas desde Telegram</div>
                </label>
              </div>

              <div className="form-group form-check">
                <input type="checkbox" id="show_prices" name="show_prices"
                  checked={!!form.show_prices} onChange={handleChange} />
                <label htmlFor="show_prices">
                  <strong>Mostrar precios</strong>
                  <div style={{fontSize:'.8rem',color:'var(--text-muted)'}}>Incluye el precio en la lista de servicios</div>
                </label>
              </div>

              <div className="form-group form-check">
                <input type="checkbox" id="show_duration" name="show_duration"
                  checked={!!form.show_duration} onChange={handleChange} />
                <label htmlFor="show_duration">
                  <strong>Mostrar duración</strong>
                  <div style={{fontSize:'.8rem',color:'var(--text-muted)'}}>Incluye la duración en la lista de servicios</div>
                </label>
              </div>

              <div className="form-group form-check">
                <input type="checkbox" id="use_global_bot" name="use_global_bot"
                  checked={!!form.use_global_bot} onChange={handleChange} />
                <label htmlFor="use_global_bot">
                  <strong>Usar bot global de Turnix</strong>
                  <div style={{fontSize:'.8rem',color:'var(--text-muted)'}}>Si está activo, el bot global identificará tu negocio por slug</div>
                </label>
              </div>
            </div>

            {config?.tenant && (
              <div className="card" style={{background:'var(--bg-muted)'}}>
                <h4 style={{margin:'0 0 .5rem 0',fontSize:'.9rem'}}>🔗 Enlace del bot</h4>
                <p style={{fontSize:'.85rem',margin:'0 0 .5rem 0',color:'var(--text-muted)'}}>
                  Comparte este enlace con tus clientes para que puedan acceder al bot de tu negocio:
                </p>
                <code style={{
                  display:'block',padding:'.5rem .75rem',background:'white',
                  borderRadius:'6px',fontSize:'.82rem',wordBreak:'break-all',
                  border:'1px solid var(--border)'
                }}>
                  https://t.me/TurnixBot?start={config?.tenant_slug || 'tu-negocio'}
                </code>
              </div>
            )}
          </div>
        </div>

        <div style={{display:'flex',justifyContent:'flex-end',marginTop:'1.5rem'}}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Guardando...' : 'Guardar configuración'}
          </button>
        </div>
      </form>
    </div>
  )
}
