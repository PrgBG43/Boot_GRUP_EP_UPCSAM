import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const STATUS_MAP = {
  connected: { label: 'Conectado', cls: 'badge-success' },
  not_connected: { label: 'No conectado', cls: 'badge-warning' },
  token_invalid: { label: 'Token invalido', cls: 'badge-danger' },
  error: { label: 'Error', cls: 'badge-danger' },
}

const MESSAGE_FIELDS = [
  { key: 'welcome_message', label: 'Mensaje de bienvenida' },
  { key: 'services_message', label: 'Mensaje para mostrar servicios' },
  { key: 'ask_name_message', label: 'Mensaje para solicitar nombre' },
  { key: 'ask_phone_message', label: 'Mensaje para solicitar telefono' },
  { key: 'ask_service_message', label: 'Mensaje para solicitar servicio' },
  { key: 'ask_date_message', label: 'Mensaje para solicitar fecha' },
  { key: 'ask_time_message', label: 'Mensaje para solicitar hora' },
  { key: 'confirm_message', label: 'Mensaje de confirmacion' },
  { key: 'unavailable_message', label: 'Mensaje de horario no disponible' },
  { key: 'cancel_message', label: 'Mensaje de cancelacion' },
  { key: 'goodbye_message', label: 'Mensaje de despedida' },
]

const OPTION_FIELDS = [
  { key: 'show_prices', label: 'Mostrar precios' },
  { key: 'show_duration', label: 'Mostrar duracion' },
  { key: 'allow_cancellation', label: 'Permitir cancelaciones' },
  { key: 'collect_phone', label: 'Solicitar telefono' },
  { key: 'require_confirmation', label: 'Requerir confirmacion antes de crear la cita' },
]

const DEFAULT_COMMANDS = `/start - Iniciar reservas
/servicios - Ver servicios
/citas - Ver mis citas
/cancelar - Cancelar una cita
/ayuda - Obtener ayuda`

function toForm(config) {
  return {
    welcome_message: config?.welcome_message || '',
    services_message: config?.services_message || '',
    ask_name_message: config?.ask_name_message || '',
    ask_phone_message: config?.ask_phone_message || '',
    ask_service_message: config?.ask_service_message || '',
    ask_date_message: config?.ask_date_message || '',
    ask_time_message: config?.ask_time_message || '',
    confirm_message: config?.confirm_message || '',
    cancel_message: config?.cancel_message || '',
    unavailable_message: config?.unavailable_message || '',
    goodbye_message: config?.goodbye_message || '',
    allow_cancellation: config?.allow_cancellation ?? true,
    show_prices: config?.show_prices ?? true,
    show_duration: config?.show_duration ?? true,
    collect_phone: config?.collect_phone ?? true,
    require_confirmation: config?.require_confirmation ?? true,
    bot_name: config?.bot_name || '',
    bot_description: config?.bot_description || '',
    bot_short_description: config?.bot_short_description || '',
    bot_commands: config?.bot_commands || DEFAULT_COMMANDS,
  }
}

function renderTemplate(text, config) {
  const values = {
    business_name: 'Barberia Demo Turnix',
    service_name: 'Corte de cabello',
    date: '2026-06-01',
    time: '10:00',
    client_name: 'Cliente Demo',
    phone: '3001234567',
    price: '$18.000',
    duration: '30 min',
  }
  return (text || '').replace(/\{(\w+)\}/g, (_, key) => values[key] ?? `{${key}}`) || config
}

export default function TelegramConfig() {
  const { isSuperadmin } = useAuth()
  const [config, setConfig] = useState(null)
  const [form, setForm] = useState(toForm(null))
  const [businesses, setBusinesses] = useState([])
  const [selectedTenant, setSelectedTenant] = useState('')
  const [botToken, setBotToken] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const selectedBusiness = useMemo(
    () => businesses.find(item => item.id === Number(selectedTenant)),
    [businesses, selectedTenant],
  )

  const tenantParam = isSuperadmin ? Number(selectedTenant) : undefined

  const loadConfig = async (tenantId) => {
    setLoading(true)
    setFeedback(null)
    try {
      const data = await api.getTelegramConfig(tenantId || undefined)
      setConfig(data)
      setForm(toForm(data))
      setBotToken('')
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isSuperadmin) {
      api.getBusinesses()
        .then(data => setBusinesses(data || []))
        .catch(err => setFeedback({ type: 'error', msg: err.message }))
        .finally(() => setLoading(false))
    } else {
      loadConfig()
    }
  }, [isSuperadmin])

  const handleTenantChange = (e) => {
    const tenantId = e.target.value
    setSelectedTenant(tenantId)
    setConfig(null)
    setForm(toForm(null))
    setBotToken('')
    if (tenantId) loadConfig(Number(tenantId))
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }

  const refreshAfterConnection = async (message) => {
    const data = await api.getTelegramConfig(tenantParam)
    setConfig(data)
    setForm(toForm(data))
    setBotToken('')
    setFeedback({ type: 'success', msg: message })
  }

  const handleConnect = async (e) => {
    e.preventDefault()
    if (!botToken.trim()) {
      setFeedback({ type: 'error', msg: 'Ingresa el token entregado por BotFather.' })
      return
    }
    setConnecting(true)
    setFeedback(null)
    try {
      await api.connectTelegramBot(botToken.trim(), tenantParam)
      await refreshAfterConnection('Bot conectado correctamente.')
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setConnecting(false)
    }
  }

  const handleValidate = async () => {
    setConnecting(true)
    setFeedback(null)
    try {
      await api.validateTelegramBot(tenantParam)
      await refreshAfterConnection('Conexion validada correctamente.')
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setConnecting(false)
    }
  }

  const handleDisconnect = async () => {
    setConnecting(true)
    setFeedback(null)
    try {
      const updated = await api.disconnectTelegramBot(tenantParam)
      setConfig(updated)
      setForm(toForm(updated))
      setFeedback({ type: 'success', msg: 'Bot desconectado.' })
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setConnecting(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const updated = await api.updateTelegramConfig(form, tenantParam)
      setConfig(updated)
      setForm(toForm(updated))
      setFeedback({ type: 'success', msg: 'Configuracion guardada correctamente.' })
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setSaving(false)
    }
  }

  const handleCopy = async () => {
    if (!config?.public_link) return
    try {
      await navigator.clipboard.writeText(config.public_link)
      setFeedback({ type: 'success', msg: 'Enlace copiado.' })
    } catch {
      setFeedback({ type: 'error', msg: 'No fue posible copiar el enlace.' })
    }
  }

  const statusInfo = STATUS_MAP[config?.connection_status] || STATUS_MAP.not_connected

  if (loading && !config && !isSuperadmin) return <div className="spinner" />

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Configuracion de Telegram</h1>
          <p>Conecta y administra el bot propio de Telegram para cada negocio.</p>
        </div>
      </div>

      {isSuperadmin && (
        <div className="card section-spacing">
          <div className="form-group form-group-compact">
            <label><strong>Seleccionar negocio</strong></label>
            <select className="filter-select tenant-config-select" value={selectedTenant} onChange={handleTenantChange}>
              <option value="">Elige un negocio</option>
              {businesses.map(business => (
                <option key={business.id} value={business.id}>{business.name}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {feedback && <div className={`alert alert-${feedback.type}`}>{feedback.msg}</div>}

      {isSuperadmin && !selectedTenant && (
        <div className="empty-state">
          <h2 className="empty-state-title">Selecciona un negocio</h2>
          <p className="empty-state-text">Elige un negocio para conectar y configurar su bot.</p>
        </div>
      )}

      {config && (
        <>
          <div className="card section-spacing">
            <h3 className="panel-heading">Estado del bot</h3>
            <div className="inline-meta">
              <span className={`badge ${statusInfo.cls}`}>{config.is_connected ? 'Conectado' : statusInfo.label}</span>
              {config.bot_name && <span>Nombre: <strong>{config.bot_name}</strong></span>}
              {config.bot_username && <span>Usuario: <strong>@{config.bot_username}</strong></span>}
              {config.bot_token_masked && <span>Token: <code>{config.bot_token_masked}</code></span>}
              {config.last_validated_at && (
                <span>Ultima validacion: {new Date(config.last_validated_at).toLocaleString('es-CO')}</span>
              )}
            </div>
            {config.public_link && (
              <div className="telegram-link-row">
                <code>{config.public_link}</code>
                <button type="button" className="btn btn-outline" onClick={handleCopy}>Copiar enlace</button>
              </div>
            )}
            <div className="form-actions">
              <button type="button" className="btn btn-outline" onClick={handleValidate} disabled={connecting || !config.is_connected}>
                Validar conexion
              </button>
              <button type="button" className="btn btn-danger" onClick={handleDisconnect} disabled={connecting || !config.is_connected}>
                Desconectar bot
              </button>
            </div>
          </div>

          <div className="card section-spacing">
            <h3 className="panel-heading">Conectar bot</h3>
            <form onSubmit={handleConnect} noValidate>
              <div className="form-group">
                <label>Token del bot de Telegram</label>
                <input
                  className="form-input"
                  type="password"
                  value={botToken}
                  onChange={e => setBotToken(e.target.value)}
                  autoComplete="off"
                  placeholder="Pega aqui el token entregado por BotFather"
                />
                <small className="form-help">
                  Crea un bot en Telegram con BotFather, copia el token y pegalo aqui para conectar este negocio con su propio bot.
                </small>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={connecting}>
                  {connecting ? 'Conectando...' : 'Conectar bot'}
                </button>
              </div>
            </form>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className="section-spacing surface-grid surface-grid--split">
              <div className="card">
                <h3 className="panel-heading">Administracion del bot</h3>
                <div className="form-group form-group-spaced">
                  <label>Nombre publico del bot</label>
                  <input className="form-input" name="bot_name" value={form.bot_name} onChange={handleChange} />
                </div>
                <div className="form-group form-group-spaced">
                  <label>Descripcion del bot</label>
                  <textarea className="form-textarea" name="bot_description" value={form.bot_description} onChange={handleChange} rows={3} />
                </div>
                <div className="form-group form-group-spaced">
                  <label>Descripcion corta</label>
                  <input className="form-input" name="bot_short_description" value={form.bot_short_description} onChange={handleChange} />
                </div>
                <div className="form-group form-group-spaced">
                  <label>Comandos del bot</label>
                  <textarea className="form-textarea" name="bot_commands" value={form.bot_commands} onChange={handleChange} rows={5} />
                </div>
                <div className="alert alert-info alert-compact">
                  La foto de perfil del bot debe configurarse desde BotFather o desde Telegram, ya que Telegram Bot API no permite modificarla directamente desde esta integracion.
                </div>
              </div>

              <div className="card">
                <h3 className="panel-heading">Opciones de comportamiento</h3>
                {OPTION_FIELDS.map(({ key, label }) => (
                  <label className="toggle-row" key={key} htmlFor={key}>
                    <input id={key} type="checkbox" name={key} checked={!!form[key]} onChange={handleChange} />
                    <span><strong>{label}</strong></span>
                  </label>
                ))}
              </div>
            </div>

            <div className="card section-spacing">
              <h3 className="panel-heading">Mensajes del bot</h3>
              <div className="surface-grid surface-grid--split">
                {MESSAGE_FIELDS.map(({ key, label }) => (
                  <div className="form-group form-group-spaced" key={key}>
                    <label>{label}</label>
                    <textarea className="form-textarea" name={key} value={form[key] || ''} onChange={handleChange} rows={2} />
                  </div>
                ))}
              </div>
            </div>

            <div className="card section-spacing">
              <h3 className="panel-heading">Vista previa</h3>
              <div className="messages-list">
                <div className="message-bubble message-outgoing">
                  <div className="message-content">{renderTemplate(form.welcome_message, 'Bienvenido.')}</div>
                </div>
                <div className="message-bubble message-outgoing">
                  <div className="message-content">{renderTemplate(form.ask_service_message, 'Selecciona un servicio.')}</div>
                </div>
                <div className="message-bubble message-outgoing">
                  <div className="message-content">{renderTemplate(form.confirm_message, 'Cita confirmada.')}</div>
                </div>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Guardando...' : 'Guardar configuracion'}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  )
}
