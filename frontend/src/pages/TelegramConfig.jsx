import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const STATUS_MAP = {
  sin_configurar: { label: 'Sin configurar', cls: 'badge-pending',   icon: '⚪' },
  conectado:      { label: 'Conectado',       cls: 'badge-confirmed', icon: '🟢' },
  token_invalido: { label: 'Token inválido',  cls: 'badge-cancelled', icon: '🔴' },
  error:          { label: 'Error',           cls: 'badge-cancelled', icon: '🟠' },
}

export default function TelegramConfig() {
  const { isSuperadmin, user } = useAuth()
  const [config,    setConfig]    = useState(null)
  const [form,      setForm]      = useState({})
  const [tokenInput,setTokenInput]= useState('')
  const [businesses,setBusinesses]= useState([])
  const [selTenant, setSelTenant] = useState(null)   // solo para superadmin
  const [loading,   setLoading]   = useState(true)
  const [saving,    setSaving]    = useState(false)
  const [validating,setValidating]= useState(false)
  const [error,     setError]     = useState(null)
  const [feedback,  setFeedback]  = useState(null)

  const loadConfig = async (tid) => {
    setLoading(true)
    setError(null)
    try {
      const params = tid ? `?tenant_id=${tid}` : ''
      const c = await api.getTelegramConfig(tid)
      setConfig(c)
      setForm({
        welcome_message:      c.welcome_message      || '',
        services_message:     c.services_message     || '',
        ask_date_message:     c.ask_date_message      || '',
        ask_time_message:     c.ask_time_message      || '',
        confirm_message:      c.confirm_message       || '',
        cancel_message:       c.cancel_message        || '',
        unavailable_message:  c.unavailable_message   || '',
        allow_cancellation:   c.allow_cancellation    ?? true,
        show_prices:          c.show_prices            ?? true,
        show_duration:        c.show_duration          ?? true,
        use_global_bot:       c.use_global_bot         ?? true,
        bot_name:             c.bot_name              || '',
        bot_description:      c.bot_description       || '',
        bot_short_description:c.bot_short_description || '',
      })
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  useEffect(() => {
    if (isSuperadmin) {
      api.getBusinesses().then(b => setBusinesses(b || []))
      setLoading(false)
    } else {
      loadConfig(null)
    }
  }, [isSuperadmin])

  const handleTenantSelect = (e) => {
    const tid = e.target.value ? parseInt(e.target.value) : null
    setSelTenant(tid)
    if (tid) loadConfig(tid)
    else { setConfig(null); setForm({}) }
  }

  const handleChange = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleValidate = async () => {
    setFeedback(null)
    if (!tokenInput.trim()) {
      setFeedback({ type: 'error', msg: 'Ingresa el token del bot antes de validar.' })
      return
    }
    setValidating(true)
    try {
      const tid = isSuperadmin ? selTenant : null
      const res = await api.validateTelegramToken(tokenInput.trim(), tid)
      if (res.ok) {
        setFeedback({ type: 'success', msg: res.message })
        setTokenInput('')
        await loadConfig(isSuperadmin ? selTenant : null)
      } else {
        setFeedback({ type: 'error', msg: res.message })
      }
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setValidating(false)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const tid = isSuperadmin ? selTenant : null
      const updated = await api.updateTelegramConfig(form, tid)
      setConfig(updated)
      setFeedback({ type: 'success', msg: '✅ Configuración guardada correctamente.' })
    } catch (e) {
      setFeedback({ type: 'error', msg: e.message })
    }
    setSaving(false)
  }

  const statusInfo = STATUS_MAP[config?.bot_status] || STATUS_MAP.sin_configurar

  if (loading && !isSuperadmin) return <div className="spinner" />

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Configuración de Telegram</h1>
          <p>
            {isSuperadmin
              ? 'Gestiona el bot de Telegram para cada negocio'
              : 'Configura y personaliza el bot de Telegram de tu negocio'}
          </p>
        </div>
      </div>

      {/* Selector de negocio (solo superadmin) */}
      {isSuperadmin && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label><strong>Seleccionar negocio</strong></label>
            <select value={selTenant || ''} onChange={handleTenantSelect} style={{ maxWidth: '400px' }}>
              <option value="">— Elige un negocio —</option>
              {businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      {feedback && (
        <div className={`alert alert-${feedback.type}`} style={{ marginBottom: '1.25rem' }}>
          {feedback.msg}
        </div>
      )}

      {/* Mostrar contenido solo si hay config cargada */}
      {config ? (
        <>
          {/* â”€â”€ Estado del bot â”€â”€ */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: '.8rem', color: 'var(--text-muted)', marginBottom: '.2rem' }}>Estado del bot</div>
                <span className={`badge ${statusInfo.cls}`}>
                  {statusInfo.icon} {statusInfo.label}
                </span>
              </div>
              {config.bot_username && (
                <div>
                  <div style={{ fontSize: '.8rem', color: 'var(--text-muted)', marginBottom: '.2rem' }}>Username</div>
                  <strong>@{config.bot_username}</strong>
                </div>
              )}
              {config.bot_token_masked && (
                <div>
                  <div style={{ fontSize: '.8rem', color: 'var(--text-muted)', marginBottom: '.2rem' }}>Token guardado</div>
                  <code style={{ fontSize: '.82rem' }}>{config.bot_token_masked}</code>
                </div>
              )}
              {config.last_validated_at && (
                <div>
                  <div style={{ fontSize: '.8rem', color: 'var(--text-muted)', marginBottom: '.2rem' }}>Última validación</div>
                  <span style={{ fontSize: '.85rem' }}>
                    {new Date(config.last_validated_at).toLocaleString('es-CO')}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* â”€â”€ Sección: conectar bot propio â”€â”€ */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>🔑 Conectar bot propio</h3>
            <p style={{ fontSize: '.875rem', color: 'var(--text-muted)', margin: '0 0 1rem' }}>
              Obtén el token de <strong>@BotFather</strong> en Telegram y pégalo aquí para conectar tu bot.
              El token no se muestra completo después de guardarse.
            </p>
            <div style={{ display: 'flex', gap: '.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div className="form-group" style={{ flex: 1, minWidth: '250px', margin: 0 }}>
                <label>Token del bot</label>
                <input
                  type="password"
                  value={tokenInput}
                  onChange={e => setTokenInput(e.target.value)}
                  placeholder="123456789:AAF_xxxx..."
                  autoComplete="off"
                />
              </div>
              <button
                type="button"
                className="btn btn-primary"
                disabled={validating || !tokenInput.trim()}
                onClick={handleValidate}
                style={{ height: '38px' }}
              >
                {validating ? 'Validando…' : '✅ Validar y conectar'}
              </button>
            </div>
            <div style={{ marginTop: '.75rem', background: 'var(--bg-muted)', borderRadius: '6px', padding: '.5rem .75rem', fontSize: '.78rem', color: 'var(--text-muted)' }}>
              <strong>Modo global:</strong> Si no conectas un bot propio, tu negocio usará el bot global de Turnix
              identificado por el slug: <code>/{config.tenant_slug || user?.tenant_id}</code>
            </div>
          </div>

          {/* â”€â”€ Formulario de personalización â”€â”€ */}
          <form onSubmit={handleSubmit}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>

              {/* Columna izquierda: mensajes */}
              <div className="card">
                <h3 style={{ marginTop: 0, marginBottom: '1.25rem', fontSize: '1rem' }}>💬 Mensajes del bot</h3>
                {[
                  { key: 'welcome_message',      label: 'Mensaje de bienvenida' },
                  { key: 'services_message',     label: 'Texto antes de servicios' },
                  { key: 'ask_date_message',     label: 'Pregunta por fecha' },
                  { key: 'ask_time_message',     label: 'Pregunta por hora' },
                  { key: 'confirm_message',      label: 'Confirmación de cita' },
                  { key: 'cancel_message',       label: 'Cancelación de cita' },
                  { key: 'unavailable_message',  label: 'Sin disponibilidad' },
                ].map(({ key, label }) => (
                  <div className="form-group" key={key}>
                    <label>{label}</label>
                    <textarea
                      name={key}
                      value={form[key] || ''}
                      onChange={handleChange}
                      rows={2}
                    />
                  </div>
                ))}
              </div>

              {/* Columna derecha: opciones + info bot */}
              <div>
                <div className="card" style={{ marginBottom: '1rem' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '1.25rem', fontSize: '1rem' }}>⚙ï¸ Opciones del bot</h3>

                  {[
                    { key: 'allow_cancellation', label: 'Permitir cancelaciones', desc: 'Los clientes pueden cancelar citas desde Telegram' },
                    { key: 'show_prices',         label: 'Mostrar precios',         desc: 'Incluye el precio en la lista de servicios' },
                    { key: 'show_duration',       label: 'Mostrar duración',        desc: 'Incluye la duración en la lista de servicios' },
                    { key: 'use_global_bot',      label: 'Usar bot global',         desc: 'Si está activo, el bot global identificará tu negocio por slug' },
                  ].map(({ key, label, desc }) => (
                    <div className="form-group form-check" key={key}>
                      <input type="checkbox" id={key} name={key}
                        checked={!!form[key]} onChange={handleChange} />
                      <label htmlFor={key}>
                        <strong>{label}</strong>
                        <div style={{ fontSize: '.8rem', color: 'var(--text-muted)' }}>{desc}</div>
                      </label>
                    </div>
                  ))}
                </div>

                <div className="card" style={{ marginBottom: '1rem' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>🤖 Perfil del bot</h3>
                  <div className="form-group">
                    <label>Nombre visible del bot</label>
                    <input name="bot_name" value={form.bot_name || ''} onChange={handleChange} placeholder="Mi Barbería Bot" />
                  </div>
                  <div className="form-group">
                    <label>Descripción corta</label>
                    <input name="bot_short_description" value={form.bot_short_description || ''} onChange={handleChange} placeholder="Agenda tu cita fácilmente" maxLength={120} />
                  </div>
                  <div className="form-group">
                    <label>Descripción completa</label>
                    <textarea name="bot_description" value={form.bot_description || ''} onChange={handleChange} rows={3} placeholder="Descripción que verán los usuarios al abrir el bot" />
                  </div>
                  <p style={{ fontSize: '.75rem', color: 'var(--text-muted)', margin: 0 }}>
                    ℹï¸ El nombre y descripción se actualizan en Telegram mediante la API (setMyName / setMyDescription).
                    Requiere que el bot esté conectado y sea válido.
                  </p>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Guardando…' : 'Guardar configuración'}
              </button>
            </div>
          </form>
        </>
      ) : (
        !isSuperadmin && !loading && (
          <div className="empty-state">
            <div className="icon">🤖</div>
            <p>No se pudo cargar la configuración de Telegram.</p>
          </div>
        )
      )}

      {isSuperadmin && !selTenant && (
        <div className="empty-state">
          <div className="icon">🏢</div>
          <p>Selecciona un negocio para configurar su Telegram.</p>
        </div>
      )}
    </div>
  )
}

