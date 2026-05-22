import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const STATUS_MAP = {
  connected: { label: 'Conectado', cls: 'badge-success' },
  not_connected: { label: 'No conectado', cls: 'badge-warning' },
  token_invalid: { label: 'Token inválido', cls: 'badge-danger' },
  error: { label: 'Error', cls: 'badge-danger' },
}

const LISTENER_STATUS_MAP = {
  active: { label: 'Activo', cls: 'badge-success' },
  inactive: { label: 'Inactivo', cls: 'badge-neutral' },
  conflict: { label: 'En conflicto', cls: 'badge-danger' },
  error: { label: 'Error', cls: 'badge-danger' },
}

const MESSAGE_FIELDS = [
  { key: 'welcome_message', label: 'Mensaje de bienvenida' },
  { key: 'services_message', label: 'Mensaje para mostrar servicios' },
  { key: 'ask_name_message', label: 'Mensaje para solicitar nombre' },
  { key: 'ask_phone_message', label: 'Mensaje para solicitar teléfono' },
  { key: 'ask_service_message', label: 'Mensaje para solicitar servicio' },
  { key: 'ask_date_message', label: 'Mensaje para solicitar fecha' },
  { key: 'ask_time_message', label: 'Mensaje para solicitar hora' },
  { key: 'confirm_message', label: 'Mensaje de confirmación' },
  { key: 'unavailable_message', label: 'Mensaje de horario no disponible' },
  { key: 'plan_limit_public_message', label: 'Mensaje público por agenda no disponible' },
  { key: 'reminder_30_message', label: 'Recordatorio Premium 30 minutos antes' },
  { key: 'reminder_15_message', label: 'Recordatorio Premium 15 minutos antes' },
  { key: 'cancel_message', label: 'Mensaje de cancelación' },
  { key: 'goodbye_message', label: 'Mensaje de despedida' },
]

const OPTION_FIELDS = [
  { key: 'show_prices', label: 'Mostrar precios' },
  { key: 'show_duration', label: 'Mostrar duración' },
  { key: 'allow_cancellation', label: 'Permitir cancelaciones' },
  { key: 'collect_phone', label: 'Solicitar teléfono' },
  { key: 'require_confirmation', label: 'Requerir confirmación antes de crear la cita' },
  { key: 'auto_start_on_greeting', label: 'Iniciar agenda cuando el cliente saluda' },
]

const ACTION_OPTIONS = [
  { value: 'iniciar_agendamiento', label: 'Iniciar agendamiento' },
  { value: 'mostrar_servicios', label: 'Mostrar servicios' },
  { value: 'mostrar_horarios', label: 'Mostrar horarios' },
  { value: 'mostrar_citas_cliente', label: 'Mostrar citas del cliente' },
  { value: 'cancelar_cita', label: 'Cancelar cita' },
  { value: 'mostrar_ayuda', label: 'Mostrar ayuda' },
  { value: 'respuesta_personalizada', label: 'Respuesta personalizada' },
]

const DEFAULT_COMMANDS = [
  {
    command: '/start',
    description: 'Iniciar reservas',
    action_type: 'iniciar_agendamiento',
    message: 'Hola. Bienvenido a {business_name}. Vamos a agendar tu cita.',
    is_active: true,
  },
  {
    command: '/servicios',
    description: 'Ver servicios',
    action_type: 'mostrar_servicios',
    message: 'Estos son nuestros servicios disponibles:',
    is_active: true,
  },
  {
    command: '/horarios',
    description: 'Ver horarios disponibles',
    action_type: 'mostrar_horarios',
    message: 'Estos son los próximos horarios disponibles:',
    is_active: true,
  },
  {
    command: '/citas',
    description: 'Ver mis citas',
    action_type: 'mostrar_citas_cliente',
    message: '',
    is_active: true,
  },
  {
    command: '/cancelar',
    description: 'Cancelar una cita',
    action_type: 'cancelar_cita',
    message: 'Vamos a revisar tus citas activas para cancelar la que elijas.',
    is_active: true,
  },
  {
    command: '/ayuda',
    description: 'Obtener ayuda',
    action_type: 'mostrar_ayuda',
    message: 'Puedes escribir /servicios para ver nuestros servicios o /start para agendar una cita.',
    is_active: true,
  },
]

function normalizeCommands(raw) {
  if (Array.isArray(raw) && raw.length) {
    return raw.map(item => ({
      command: item.command?.startsWith('/') ? item.command : `/${item.command || ''}`,
      description: item.description || '',
      action_type: item.action_type || 'respuesta_personalizada',
      message: item.message || '',
      is_active: item.is_active ?? true,
    }))
  }

  if (typeof raw === 'string' && raw.trim()) {
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return normalizeCommands(parsed)
    } catch {
      return raw.split('\n').filter(Boolean).map(line => {
        const [command, description = ''] = line.includes(' - ') ? line.split(' - ') : line.split(':')
        return {
          command: command?.trim().startsWith('/') ? command.trim() : `/${command?.trim() || ''}`,
          description: description.trim(),
          action_type: 'respuesta_personalizada',
          message: '',
          is_active: true,
        }
      })
    }
  }

  return DEFAULT_COMMANDS.map(item => ({ ...item }))
}

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
    plan_limit_public_message: config?.plan_limit_public_message || '',
    reminder_30_message: config?.reminder_30_message || '',
    reminder_15_message: config?.reminder_15_message || '',
    goodbye_message: config?.goodbye_message || '',
    allow_cancellation: config?.allow_cancellation ?? true,
    auto_start_on_greeting: config?.auto_start_on_greeting ?? false,
    show_prices: config?.show_prices ?? true,
    show_duration: config?.show_duration ?? true,
    collect_phone: config?.collect_phone ?? true,
    require_confirmation: config?.require_confirmation ?? true,
    bot_name: config?.bot_name || '',
    bot_description: config?.bot_description || '',
    bot_short_description: config?.bot_short_description || '',
    bot_commands: normalizeCommands(config?.bot_commands),
  }
}

function renderTemplate(text, fallback) {
  const values = {
    business_name: 'Barbería Centro Turnix',
    service_name: 'Corte de cabello',
    date: '2026-06-01',
    time: '10:00',
    client_name: 'Cliente Prueba',
    phone: '3001234567',
    price: '$18.000',
    duration: '30 min',
  }
  return (text || '').replace(/\{(\w+)\}/g, (_, key) => values[key] ?? `{${key}}`) || fallback
}

function logoUrl(config) {
  if (!config?.internal_logo_url) return ''
  const version = config.internal_logo_updated_at || config.updated_at || Date.now()
  return `${api.assetUrl(config.internal_logo_url)}?v=${encodeURIComponent(version)}`
}

function formatDateTime(value) {
  return value ? new Date(value).toLocaleString('es-CO') : 'Sin registro'
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
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState('')
  const [removeLogo, setRemoveLogo] = useState(false)

  const selectedBusiness = useMemo(
    () => businesses.find(item => item.id === Number(selectedTenant)),
    [businesses, selectedTenant],
  )

  const tenantParam = isSuperadmin ? Number(selectedTenant) : undefined
  const savedForm = useMemo(() => toForm(config), [config])
  const hasChanges = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(savedForm) || !!logoFile || removeLogo,
    [form, savedForm, logoFile, removeLogo],
  )

  const loadConfig = async (tenantId) => {
    setLoading(true)
    setFeedback(null)
    try {
      const data = await api.getTelegramConfig(tenantId || undefined)
      setConfig(data)
      setForm(toForm(data))
      setBotToken('')
      setLogoFile(null)
      setLogoPreview('')
      setRemoveLogo(false)
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isSuperadmin) {
      api.getBusinesses({ page_size: 100 })
        .then(data => setBusinesses(data?.items || data || []))
        .catch(err => setFeedback({ type: 'error', msg: err.message }))
        .finally(() => setLoading(false))
    } else {
      loadConfig()
    }
  }, [isSuperadmin])

  useEffect(() => () => {
    if (logoPreview) URL.revokeObjectURL(logoPreview)
  }, [logoPreview])

  const handleTenantChange = (e) => {
    const tenantId = e.target.value
    setSelectedTenant(tenantId)
    setConfig(null)
    setForm(toForm(null))
    setBotToken('')
    setLogoFile(null)
    setLogoPreview('')
    setRemoveLogo(false)
    if (tenantId) loadConfig(Number(tenantId))
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleCommandChange = (index, field, value) => {
    setForm(current => ({
      ...current,
      bot_commands: current.bot_commands.map((item, i) => (
        i === index ? { ...item, [field]: field === 'is_active' ? value === true : value } : item
      )),
    }))
  }

  const addCommand = () => {
    setForm(current => ({
      ...current,
      bot_commands: [
        ...current.bot_commands,
        { command: '/', description: '', action_type: 'respuesta_personalizada', message: '', is_active: true },
      ],
    }))
  }

  const removeCommand = (index) => {
    setForm(current => ({
      ...current,
      bot_commands: current.bot_commands.filter((_, i) => i !== index),
    }))
  }

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (logoPreview) URL.revokeObjectURL(logoPreview)
    setLogoFile(file)
    setLogoPreview(URL.createObjectURL(file))
    setRemoveLogo(false)
  }

  const handleRemoveLogo = () => {
    if (logoPreview) URL.revokeObjectURL(logoPreview)
    setLogoFile(null)
    setLogoPreview('')
    setRemoveLogo(true)
  }

  const refreshAfterConnection = async (message, waitForListener = false) => {
    if (waitForListener) {
      await new Promise(resolve => setTimeout(resolve, 1200))
    }
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
      const result = await api.connectTelegramBot(botToken.trim(), tenantParam)
      await refreshAfterConnection(result?.message || 'Bot conectado correctamente. El servicio de Telegram está activo.', true)
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
      const result = await api.validateTelegramBot(tenantParam)
      await refreshAfterConnection(result?.message || 'Conexión validada correctamente.', true)
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
      let updated = await api.updateTelegramConfig(form, tenantParam)
      if (logoFile) {
        updated = await api.uploadTelegramInternalLogo(logoFile, tenantParam)
      } else if (removeLogo && config?.internal_logo_url) {
        updated = await api.removeTelegramInternalLogo(tenantParam)
      }
      setConfig(updated)
      setForm(toForm(updated))
      setLogoFile(null)
      setLogoPreview('')
      setRemoveLogo(false)
      setFeedback({ type: 'success', msg: 'Cambios guardados correctamente.' })
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
  const listenerInfo = LISTENER_STATUS_MAP[config?.listener_status] || LISTENER_STATUS_MAP.inactive
  const previewLogo = removeLogo ? '' : (logoPreview || logoUrl(config))

  if (loading && !config && !isSuperadmin) return <div className="spinner" />

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Configuración de Telegram</h1>
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
              <span>Bot conectado: <span className={`badge ${statusInfo.cls}`}>{config.is_connected ? 'Sí' : 'No'}</span></span>
              <span>Servicio de escucha: <span className={`badge ${listenerInfo.cls}`}>{config.listener_active ? 'Activo' : listenerInfo.label}</span></span>
              {selectedBusiness && <span>Negocio: <strong>{selectedBusiness.name}</strong></span>}
              {config.bot_name && <span>Nombre: <strong>{config.bot_name}</strong></span>}
              {config.bot_username && <span>Usuario: <strong>@{config.bot_username}</strong></span>}
              {config.bot_token_masked && <span>Token: <code>{config.bot_token_masked}</code></span>}
              <span>Última validación: {formatDateTime(config.last_validated_at)}</span>
              <span>Último mensaje recibido: {formatDateTime(config.last_message_received_at)}</span>
            </div>
            {config.is_connected && (
              <div className={`alert alert-compact telegram-note ${config.listener_active ? 'alert-success' : 'alert-warning'}`}>
                {config.listener_active
                  ? 'El bot está conectado y escuchando mensajes.'
                  : 'El bot está conectado, pero el servicio de Telegram no está escuchando mensajes.'}
              </div>
            )}
            {config.last_bot_error && (
              <div className="alert alert-error alert-compact telegram-note">
                Último error del bot: {config.last_bot_error}
              </div>
            )}
            {config.public_link && (
              <div className="telegram-link-row">
                <code>{config.public_link}</code>
                <button type="button" className="btn btn-outline" onClick={handleCopy}>Copiar enlace</button>
              </div>
            )}
            <div className="form-actions">
              <button type="button" className="btn btn-outline" onClick={handleValidate} disabled={connecting || !config.is_connected}>
                Validar conexión
              </button>
              <button type="button" className="btn btn-danger" onClick={handleDisconnect} disabled={connecting || !config.is_connected}>
                Desconectar bot
              </button>
            </div>
          </div>

          <div className="card section-spacing">
            <h3 className="panel-heading">Conexión del bot</h3>
            <form onSubmit={handleConnect} noValidate>
              <div className="form-group">
                <label>Token del bot de Telegram</label>
                <input
                  className="form-input"
                  type="password"
                  value={botToken}
                  onChange={e => setBotToken(e.target.value)}
                  autoComplete="off"
                  placeholder="Pega aquí el token entregado por BotFather"
                />
                <small className="form-help">
                  El token se guarda protegido y después solo se muestra enmascarado.
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
                <h3 className="panel-heading">Perfil del bot</h3>
                <div className="form-group form-group-spaced">
                  <label>Nombre público del bot</label>
                  <input className="form-input" name="bot_name" value={form.bot_name} onChange={handleChange} />
                </div>
                <div className="form-group form-group-spaced">
                  <label>Descripción</label>
                  <textarea className="form-textarea" name="bot_description" value={form.bot_description} onChange={handleChange} rows={3} />
                </div>
                <div className="form-group form-group-spaced">
                  <label>Descripción corta</label>
                  <input className="form-input" name="bot_short_description" value={form.bot_short_description} onChange={handleChange} />
                </div>
                <small className="form-help">
                  Turnix sincroniza nombre, descripción, descripción corta y comandos con Telegram cuando el bot está conectado.
                </small>
              </div>

              <div className="card">
                <h3 className="panel-heading">Imagen o logo interno</h3>
                <div className="telegram-logo-preview">
                  {previewLogo ? (
                    <img src={previewLogo} alt="Logo interno del bot" />
                  ) : (
                    <span>Sin logo</span>
                  )}
                </div>
                <div className="form-group form-group-spaced">
                  <label>Foto del bot (JPG)</label>
                  <input
                    className="form-input"
                    type="file"
                    accept="image/jpeg"
                    onChange={handleLogoChange}
                  />
                </div>
                {(config.internal_logo_url || logoPreview) && (
                  <button type="button" className="btn btn-outline btn-sm" onClick={handleRemoveLogo}>
                    Quitar logo interno
                  </button>
                )}
                <div className="alert alert-info alert-compact telegram-note">
                  Al guardar una imagen JPG, Turnix actualiza la foto real del bot mediante Telegram Bot API
                  y guarda una copia interna para identificarlo dentro del panel.
                </div>
              </div>
            </div>

            <div className="card section-spacing">
              <div className="card-header-row">
                <h3>Comandos del bot</h3>
                <button type="button" className="btn btn-outline btn-sm" onClick={addCommand}>Agregar comando</button>
              </div>
              <div className="telegram-command-list">
                {form.bot_commands.map((command, index) => (
                  <div className="telegram-command-row" key={`${command.command}-${index}`}>
                    <div className="form-row">
                      <div className="form-group">
                        <label>Comando</label>
                        <input
                          className="form-input"
                          value={command.command}
                          onChange={e => handleCommandChange(index, 'command', e.target.value)}
                          placeholder="/ayuda"
                        />
                      </div>
                      <div className="form-group">
                        <label>Descripción visible en Telegram</label>
                        <input
                          className="form-input"
                          value={command.description}
                          onChange={e => handleCommandChange(index, 'description', e.target.value)}
                          placeholder="Obtener ayuda"
                        />
                      </div>
                      <div className="form-group">
                        <label>Acción</label>
                        <select
                          className="form-select"
                          value={command.action_type}
                          onChange={e => handleCommandChange(index, 'action_type', e.target.value)}
                        >
                          {ACTION_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="form-group form-group-spaced">
                      <label>Mensaje asociado</label>
                      <textarea
                        className="form-textarea"
                        value={command.message || ''}
                        onChange={e => handleCommandChange(index, 'message', e.target.value)}
                        rows={2}
                        placeholder="Mensaje opcional para este comando"
                      />
                    </div>
                    <div className="telegram-command-actions">
                      <label className="toggle-row toggle-row-inline">
                        <input
                          type="checkbox"
                          checked={!!command.is_active}
                          onChange={e => handleCommandChange(index, 'is_active', e.target.checked)}
                        />
                        <span><strong>Activo</strong></span>
                      </label>
                      <button type="button" className="btn btn-outline btn-sm" onClick={() => removeCommand(index)}>
                        Quitar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="section-spacing surface-grid surface-grid--split">
              <div className="card">
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

              <div className="card">
                <h3 className="panel-heading">Opciones de comportamiento</h3>
                <div className="alert alert-info alert-compact">
                  Los recordatorios automáticos de 30 y 15 minutos se envían solo para negocios Premium.
                </div>
                {OPTION_FIELDS.map(({ key, label }) => (
                  <label className="toggle-row" key={key} htmlFor={key}>
                    <input id={key} type="checkbox" name={key} checked={!!form[key]} onChange={handleChange} />
                    <span><strong>{label}</strong></span>
                  </label>
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

            <div className="form-actions telegram-sticky-actions">
              <button type="submit" className="btn btn-primary" disabled={saving || !hasChanges}>
                {saving ? 'Guardando...' : 'Guardar cambios'}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  )
}
