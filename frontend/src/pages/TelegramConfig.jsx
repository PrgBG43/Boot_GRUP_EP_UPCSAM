import { useEffect, useMemo, useState } from 'react'
import { AlertMessage } from '../components/FormMessages.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'

const STATUS_MAP = {
  sin_configurar: { label: 'Sin configurar', cls: 'badge-pending' },
  conectado: { label: 'Conectado', cls: 'badge-confirmed' },
  token_invalido: { label: 'Token inválido', cls: 'badge-cancelled' },
  error: { label: 'Error', cls: 'badge-cancelled' },
}

const MESSAGE_FIELDS = [
  { key: 'welcome_message', label: 'Mensaje de bienvenida' },
  { key: 'services_message', label: 'Texto antes de servicios' },
  { key: 'ask_date_message', label: 'Pregunta por fecha' },
  { key: 'ask_time_message', label: 'Pregunta por hora' },
  { key: 'confirm_message', label: 'Confirmación de cita' },
  { key: 'cancel_message', label: 'Cancelación de cita' },
  { key: 'unavailable_message', label: 'Sin disponibilidad' },
]

const OPTION_FIELDS = [
  { key: 'allow_cancellation', label: 'Permitir cancelaciones', desc: 'Los clientes pueden cancelar citas desde Telegram.' },
  { key: 'show_prices', label: 'Mostrar precios', desc: 'Incluye el precio en la lista de servicios.' },
  { key: 'show_duration', label: 'Mostrar duración', desc: 'Incluye la duración en la lista de servicios.' },
]

function toForm(config) {
  return {
    welcome_message: config?.welcome_message || '',
    services_message: config?.services_message || '',
    ask_date_message: config?.ask_date_message || '',
    ask_time_message: config?.ask_time_message || '',
    confirm_message: config?.confirm_message || '',
    cancel_message: config?.cancel_message || '',
    unavailable_message: config?.unavailable_message || '',
    allow_cancellation: config?.allow_cancellation ?? true,
    show_prices: config?.show_prices ?? true,
    show_duration: config?.show_duration ?? true,
    use_global_bot: true,
  }
}

export default function TelegramConfig() {
  const { isSuperadmin } = useAuth()
  const [config, setConfig] = useState(null)
  const [form, setForm] = useState(toForm(null))
  const [businesses, setBusinesses] = useState([])
  const [selectedTenant, setSelectedTenant] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const selectedBusiness = useMemo(
    () => businesses.find(item => item.id === Number(selectedTenant)),
    [businesses, selectedTenant],
  )

  const loadConfig = async (tenantId) => {
    setLoading(true)
    setFeedback(null)
    try {
      const data = await api.getTelegramConfig(tenantId || undefined)
      setConfig(data)
      setForm(toForm(data))
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
    if (tenantId) loadConfig(Number(tenantId))
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(current => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      const updated = await api.updateTelegramConfig({ ...form, use_global_bot: true }, isSuperadmin ? Number(selectedTenant) : undefined)
      setConfig(updated)
      setForm(toForm(updated))
      setFeedback({ type: 'success', msg: 'Configuración guardada correctamente.' })
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message })
    } finally {
      setSaving(false)
    }
  }

  const handleCopy = async () => {
    if (!config?.public_bot_link) return
    try {
      await navigator.clipboard.writeText(config.public_bot_link)
      setFeedback({ type: 'success', msg: 'Enlace copiado.' })
    } catch {
      setFeedback({ type: 'error', msg: 'No fue posible copiar el enlace.' })
    }
  }

  const statusInfo = STATUS_MAP[config?.bot_status] || STATUS_MAP.sin_configurar

  if (loading && !config && !isSuperadmin) return <div className="spinner" />

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Configuración de Telegram</h1>
          <p>Administra el enlace público, mensajes y comportamiento del bot global de Turnix.</p>
        </div>
      </div>

      {isSuperadmin && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label><strong>Seleccionar negocio</strong></label>
            <select value={selectedTenant} onChange={handleTenantChange} style={{ maxWidth: '420px' }}>
              <option value="">Elige un negocio</option>
              {businesses.map(business => (
                <option key={business.id} value={business.id}>{business.name}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {feedback && <AlertMessage type={feedback.type}>{feedback.msg}</AlertMessage>}

      {isSuperadmin && !selectedTenant && (
        <div className="empty-state">
          <p>Selecciona un negocio para configurar Telegram.</p>
        </div>
      )}

      {config && (
        <>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>Enlace público del bot</h3>
            {config.public_bot_link ? (
              <div className="telegram-link-row">
                <code>{config.public_bot_link}</code>
                <button type="button" className="btn btn-outline" onClick={handleCopy}>Copiar enlace</button>
              </div>
            ) : (
              <div className="alert alert-info" style={{ marginBottom: 0 }}>
                Configura TELEGRAM_BOT_TOKEN en el archivo .env y ejecuta el bot para habilitar el enlace público. Si el username no se detecta, define TELEGRAM_BOT_USERNAME.
              </div>
            )}
            <div style={{ marginTop: '.75rem', color: 'var(--text-muted)', fontSize: '.85rem' }}>
              Identificador del negocio: <code>{config.tenant_slug || selectedBusiness?.slug || 'sin-slug'}</code>
            </div>
          </div>

          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>Estado de conexión</h3>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <span className={`badge ${statusInfo.cls}`}>{statusInfo.label}</span>
              {config.bot_username && <span>Bot: <strong>@{config.bot_username}</strong></span>}
              {config.last_validated_at && (
                <span>Última validación: {new Date(config.last_validated_at).toLocaleString('es-CO')}</span>
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(280px, .7fr)', gap: '1.5rem' }}>
              <div className="card">
                <h3 style={{ marginTop: 0, marginBottom: '1.25rem', fontSize: '1rem' }}>Mensajes del bot</h3>
                {MESSAGE_FIELDS.map(({ key, label }) => (
                  <div className="form-group" key={key}>
                    <label>{label}</label>
                    <textarea name={key} value={form[key] || ''} onChange={handleChange} rows={2} />
                  </div>
                ))}
              </div>

              <div className="card">
                <h3 style={{ marginTop: 0, marginBottom: '1.25rem', fontSize: '1rem' }}>Opciones de comportamiento</h3>
                {OPTION_FIELDS.map(({ key, label, desc }) => (
                  <label className="toggle-row" key={key} htmlFor={key}>
                    <input id={key} type="checkbox" name={key} checked={!!form[key]} onChange={handleChange} />
                    <span>
                      <strong>{label}</strong>
                      <small>{desc}</small>
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Guardando...' : 'Guardar configuración'}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  )
}
