import { useEffect, useState } from 'react'
import api from '../../api.js'

// -- Generación automática de slug ---------------------------
function generateSlug(name) {
  return (name || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

// -- Validación de teléfono -------------------------------------
// 10 dígitos exactos, comienza por 3, sin espacios ni guiones
function validatePhone(phone) {
  if (!phone || !phone.trim()) return 'El teléfono es obligatorio.'
  if (!/^3[0-9]{9}$/.test(phone.trim())) {
    return 'El teléfono debe tener 10 dígitos y comenzar por 3.'
  }
  return null
}

// -- Componente de error de campo -----------------------------
function FieldError({ msg }) {
  if (!msg) return null
  return <span className="field-error">{msg}</span>
}

// -- Estado inicial de formularios ----------------------------
const EMPTY_TENANT = {
  name: '', description: '', phone: '', address: '', city: '', city_id: '',
  state_id: '', slug: '', opening_time: '08:00', closing_time: '20:00',
  plan_id: '', is_active: true,
}
const EMPTY_ADMIN = {
  first_name: '', last_name: '', email: '', password: '', confirm_password: '', phone: '',
}

// -- Opciones de filtro por plan ------------------------------
const PLAN_FILTERS = [
  { value: '',           label: 'Todos' },
  { value: 'free',       label: 'Gratuito' },
  { value: 'premium',    label: 'Premium' },
  { value: 'enterprise', label: 'Empresarial' },
]

// -- Función de normalización para PDF -----------------------
function pdfText(text) {
  if (!text) return '-'
  return String(text)
    .replace(/á/g,'a').replace(/é/g,'e').replace(/í/g,'i')
    .replace(/ó/g,'o').replace(/ú/g,'u').replace(/ü/g,'u')
    .replace(/Á/g,'A').replace(/É/g,'E').replace(/Í/g,'I')
    .replace(/Ó/g,'O').replace(/Ú/g,'U').replace(/Ü/g,'U')
    .replace(/ñ/g,'n').replace(/Ñ/g,'N')
}

// ------------------------------------------------------------
export default function AdminTenants() {
  const [tenants, setTenants]     = useState([])
  const [plans, setPlans]         = useState([])
  const [states, setStates]       = useState([])
  const [cities, setCities]       = useState([])
  const [loading, setLoading]     = useState(true)
  const [modal, setModal]         = useState(null)
  const [tenantForm, setTenantForm] = useState(EMPTY_TENANT)
  const [adminForm, setAdminForm]   = useState(EMPTY_ADMIN)
  const [editing, setEditing]     = useState(null)
  const [saving, setSaving]       = useState(false)
  const [feedback, setFeedback]   = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [planFilter, setPlanFilter] = useState('')

  // -- Carga de datos ---------------------------------------
  const load = async () => {
    setLoading(true)
    try {
      const params = planFilter ? { plan: planFilter } : {}
      const [t, p, s] = await Promise.all([
        api.getBusinesses(params),
        api.getPlans(),
        api.getStates(),
      ])
      setTenants(t || [])
      setPlans(p || [])
      setStates(s || [])
    } catch (err) {
      const msg = err.message || ''
      if (msg.includes('401') || msg.includes('sesión') || msg.includes('Unauthorized')) {
        setFeedback('La sesión expiró. Inicia sesión nuevamente.')
      } else if (msg.includes('403') || msg.includes('permiso') || msg.includes('Forbidden')) {
        setFeedback('No tienes permiso para consultar los negocios.')
      } else if (msg.includes('500') || msg.includes('Internal')) {
        setFeedback('No fue posible cargar los negocios. Revisa el estado del servidor.')
      } else if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('fetch')) {
        setFeedback('No se pudo establecer conexión con el servidor.')
      } else {
        setFeedback('Error al cargar los datos: ' + msg)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [planFilter])  // eslint-disable-line react-hooks/exhaustive-deps

  // -- Carga de ciudades cuando cambia el departamento ------
  useEffect(() => {
    if (tenantForm.state_id) {
      api.getCities(tenantForm.state_id)
        .then(c => setCities(c || []))
        .catch(() => setCities([]))
    } else {
      setCities([])
    }
  }, [tenantForm.state_id])

  // -- Apertura de modales ----------------------------------
  const openCreate = () => {
    setTenantForm(EMPTY_TENANT)
    setAdminForm(EMPTY_ADMIN)
    setCities([])
    setEditing(null)
    setModal('create')
    setFeedback(null)
    setFieldErrors({})
  }

  const openEdit = (t) => {
    setTenantForm({
      name: t.name || '',
      description: t.description || '',
      phone: t.phone || '',
      address: t.address || '',
      city: t.city_name || t.city || '',
      city_id: t.city_id || '',
      state_id: t.state_id || '',
      slug: t.slug || '',
      opening_time: t.opening_time || '08:00',
      closing_time: t.closing_time || '20:00',
      plan_id: t.plan?.id || '',
      is_active: t.is_active,
    })
    setEditing(t.id)
    setModal('edit')
    setFeedback(null)
    setFieldErrors({})
    setCities([])
  }

  // -- Manejadores de cambio en formularios -----------------
  const handleTenantChange = (e) => {
    const { name, value, type, checked } = e.target
    const newVal = type === 'checkbox' ? checked : value

    if (name === 'state_id') {
      // Resetear ciudad al cambiar departamento
      setTenantForm(f => ({ ...f, state_id: value, city_id: '', city: '' }))
    } else if (name === 'name' && modal === 'create') {
      // Auto-generar slug al escribir el nombre (solo en modo crear)
      setTenantForm(f => ({ ...f, name: value, slug: generateSlug(value) }))
    } else if (name === 'phone') {
      // Solo permitir dígitos, máximo 10 caracteres
      const digits = value.replace(/\D/g, '').slice(0, 10)
      setTenantForm(f => ({ ...f, phone: digits }))
    } else {
      setTenantForm(f => ({ ...f, [name]: newVal }))
    }

    // Limpiar error del campo al editarlo
    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: null }))
    }
  }

  const handleAdminChange = (e) => {
    const { name, value } = e.target
    setAdminForm(f => ({ ...f, [name]: value }))
    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: null }))
    }
  }

  // -- Validación formulario Crear --------------------------
  const validateCreate = () => {
    const errs = {}

    // Datos del negocio
    if (!tenantForm.name.trim())        errs.name        = 'El nombre comercial es obligatorio.'
    if (!tenantForm.description.trim()) errs.description = 'La descripción es obligatoria.'
    if (!tenantForm.address.trim())     errs.address     = 'La dirección es obligatoria.'
    if (!tenantForm.plan_id)            errs.plan_id     = 'Selecciona un plan.'
    if (!tenantForm.opening_time)       errs.opening_time = 'El horario de apertura es obligatorio.'
    if (!tenantForm.closing_time)       errs.closing_time = 'El horario de cierre es obligatorio.'
    if (!tenantForm.state_id)           errs.state_id    = 'Selecciona un departamento.'
    if (!tenantForm.city_id)            errs.city        = 'Selecciona una ciudad.'

    if (tenantForm.opening_time && tenantForm.closing_time &&
        tenantForm.closing_time <= tenantForm.opening_time) {
      errs.closing_time = 'El horario de cierre debe ser posterior al de apertura.'
    }

    const phoneErr = validatePhone(tenantForm.phone)
    if (phoneErr) errs.phone = phoneErr

    // Datos del administrador
    if (!adminForm.first_name.trim()) errs.first_name = 'El nombre del administrador es obligatorio.'
    if (!adminForm.last_name.trim())  errs.last_name  = 'El apellido del administrador es obligatorio.'
    if (!adminForm.email.trim())      errs.email      = 'El correo electrónico es obligatorio.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(adminForm.email))
      errs.email = 'Ingresa un correo electrónico válido.'

    if (!adminForm.password)           errs.password         = 'La contraseña es obligatoria.'
    else if (adminForm.password.length < 8)
      errs.password = 'La contraseña debe tener al menos 8 caracteres.'

    if (!adminForm.confirm_password)
      errs.confirm_password = 'Confirma la contraseña.'
    else if (adminForm.password !== adminForm.confirm_password)
      errs.confirm_password = 'Las contraseñas no coinciden.'

    return errs
  }

  // -- Enviar formulario Crear ------------------------------
  const handleSubmitCreate = async (e) => {
    e.preventDefault()
    setFeedback(null)

    const errs = validateCreate()
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs)
      setFeedback('Corrige los errores del formulario antes de continuar.')
      return
    }

    setSaving(true)
    try {
      await api.createBusinessWithAdmin({
        business: {
          name:         tenantForm.name.trim(),
          description:  tenantForm.description.trim(),
          phone:        tenantForm.phone.trim(),
          address:      tenantForm.address.trim(),
          state_id:     parseInt(tenantForm.state_id),
          city_id:      parseInt(tenantForm.city_id),
          slug:         tenantForm.slug || undefined,
          opening_time: tenantForm.opening_time,
          closing_time: tenantForm.closing_time,
          plan_id:      parseInt(tenantForm.plan_id),
          is_active:    tenantForm.is_active,
        },
        admin: {
          first_name:       adminForm.first_name.trim(),
          last_name:        adminForm.last_name.trim(),
          email:            adminForm.email.trim(),
          password:         adminForm.password,
          confirm_password: adminForm.confirm_password,
          phone:            adminForm.phone.trim() || undefined,
        },
      })
      setModal(null)
      load()
    } catch (err) {
      const msg = err.message || 'Error al crear el negocio.'
      if (msg.toLowerCase().includes('email')) {
        setFieldErrors(prev => ({ ...prev, email: 'El correo ya está registrado.' }))
        setFeedback('Corrige los errores del formulario antes de continuar.')
      } else if (msg.toLowerCase().includes('teléfono') || msg.toLowerCase().includes('telefono') || msg.toLowerCase().includes('phone')) {
        setFieldErrors(prev => ({ ...prev, phone: 'El teléfono debe tener 10 dígitos y comenzar por 3.' }))
        setFeedback('Corrige los errores del formulario antes de continuar.')
      } else {
        setFeedback(msg)
      }
    } finally {
      setSaving(false)
    }
  }

  // -- Validación formulario Editar -------------------------
  const validateEdit = () => {
    const errs = {}
    if (!tenantForm.name.trim()) errs.name = 'El nombre del negocio es obligatorio.'
    if (tenantForm.phone) {
      const phoneErr = validatePhone(tenantForm.phone)
      if (phoneErr) errs.phone = phoneErr
    }
    return errs
  }

  // -- Enviar formulario Editar -----------------------------
  const handleSubmitEdit = async (e) => {
    e.preventDefault()
    setFeedback(null)

    const errs = validateEdit()
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs)
      setFeedback('Corrige los errores antes de continuar.')
      return
    }

    setSaving(true)
    try {
      const payload = {
        name:         tenantForm.name.trim(),
        description:  tenantForm.description || null,
        phone:        tenantForm.phone || null,
        address:      tenantForm.address || null,
        opening_time: tenantForm.opening_time || null,
        closing_time: tenantForm.closing_time || null,
        plan_id:      tenantForm.plan_id ? parseInt(tenantForm.plan_id) : null,
        is_active:    tenantForm.is_active,
        state_id:     tenantForm.state_id ? parseInt(tenantForm.state_id) : null,
        city_id:      tenantForm.city_id ? parseInt(tenantForm.city_id) : null,
      }
      await api.updateBusiness(editing, payload)
      setModal(null)
      load()
    } catch (err) {
      const msg = err.message || 'Error al actualizar el negocio.'
      if (msg.toLowerCase().includes('teléfono') || msg.toLowerCase().includes('phone')) {
        setFieldErrors(prev => ({ ...prev, phone: msg }))
      }
      setFeedback(msg)
    } finally {
      setSaving(false)
    }
  }

  // -- Activar / Desactivar ---------------------------------
  const toggleActive = async (t) => {
    try {
      if (t.is_active) await api.deactivateTenant(t.id)
      else             await api.activateTenant(t.id)
      load()
    } catch (err) {
      setFeedback(err.message)
    }
  }

  // -- Descargar PDF ----------------------------------------
  const downloadPDF = async () => {
    const { jsPDF }             = await import('jspdf')
    const { default: autoTable } = await import('jspdf-autotable')

    const doc         = new jsPDF()
    const filterLabel = PLAN_FILTERS.find(o => o.value === planFilter)?.label || 'Todos'
    const fecha       = new Date().toLocaleDateString('es-CO', {
      year: 'numeric', month: 'long', day: 'numeric',
    })

    doc.setFontSize(16)
    doc.setFont(undefined, 'bold')
    doc.text(pdfText('Reporte de negocios registrados en Turnix'), 14, 20)

    doc.setFontSize(11)
    doc.setFont(undefined, 'normal')
    doc.text(`Filtro aplicado: ${pdfText(filterLabel)}`, 14, 30)
    doc.text(`Fecha de generación: ${pdfText(fecha)}`, 14, 38)

    autoTable(doc, {
      startY: 46,
      head: [['Negocio', 'Departamento', 'Ciudad', 'Teléfono', 'Administrador', 'Correo admin', 'Plan', 'Estado']],
      body: tenants.map(t => {
        const adName = t.owner_user
          ? `${t.owner_user.first_name || ''} ${t.owner_user.last_name || ''}`.trim()
          : '-'
        return [
          pdfText(t.name),
          pdfText(t.state_name),
          pdfText(t.city_name || t.city),
          pdfText(t.phone),
          pdfText(adName),
          pdfText(t.owner_user?.email),
          pdfText(t.plan?.display_name),
          t.is_active ? 'Activo' : 'Inactivo',
        ]
      }),
      styles:     { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [108, 63, 197], textColor: 255 },
      alternateRowStyles: { fillColor: [248, 248, 252] },
    })

    const pageCount = doc.internal.getNumberOfPages()
    doc.setFontSize(8)
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i)
      doc.text(
        'Reporte generado desde Turnix.',
        14,
        doc.internal.pageSize.height - 10,
      )
    }

    doc.save(`turnix-negocios-${planFilter || 'todos'}.pdf`)
  }

  // -- Helpers de UI ----------------------------------------
  const planName    = (t) => t.plan?.display_name || '—'
  const adminName   = (t) => t.owner_user
    ? `${t.owner_user.first_name || ''} ${t.owner_user.last_name || ''}`.trim() || '—'
    : '—'
  const adminEmail  = (t) => t.owner_user?.email || '—'
  const planBadgeClass = (t) => {
    const raw = `${t.plan?.name || ''} ${t.plan?.display_name || ''}`.toLowerCase()
    if (raw.includes('enterprise') || raw.includes('empresarial')) return 'badge-enterprise'
    if (raw.includes('premium')) return 'badge-premium'
    return 'badge-free'
  }
  const statusBadge = (active) => (
    <span className={`badge ${active ? 'badge-success' : 'badge-neutral'}`}>
      {active ? 'Activo' : 'Inactivo'}
    </span>
  )

  if (loading) return <div className="spinner" />

  // --------------------------------------------------------
  return (
    <div>
      {/* Encabezado */}
      <div className="page-header">
        <div>
          <h1>Negocios</h1>
          <p>Gestión de negocios registrados en la plataforma</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Crear negocio</button>
      </div>

      {/* Mini-estadísticas */}
      <div className="stats-row">
        <div className="mini-stat"><strong>{tenants.length}</strong><span>Total</span></div>
        <div className="mini-stat"><strong>{tenants.filter(t => t.is_active).length}</strong><span>Activos</span></div>
        <div className="mini-stat"><strong>{tenants.filter(t => !t.is_active).length}</strong><span>Inactivos</span></div>
      </div>

      {/* Barra de filtros + PDF */}
      <div className="page-toolbar">
        <div className="filter-group">
          {PLAN_FILTERS.map(opt => (
            <button
              key={opt.value}
              className={`filter-pill${planFilter === opt.value ? ' active' : ''}`}
              onClick={() => setPlanFilter(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="action-group">
          <button className="btn btn-secondary" onClick={downloadPDF} title="Descargar PDF con el filtro actual">
            Descargar PDF
          </button>
        </div>
      </div>

      {/* Alerta global */}
      {feedback && !modal && (
        <div className="alert alert-error">{feedback}</div>
      )}

      {/* Tabla o estado vacío */}
      {tenants.length === 0 ? (
        <div className="empty-state">
          <h2 className="empty-state-title">
            {planFilter ? 'Sin negocios para este plan' : 'Sin negocios registrados'}
          </h2>
          <p className="empty-state-text">
            {planFilter ? 'No hay negocios con el plan seleccionado.' : 'Crea el primer negocio para empezar a gestionar la plataforma.'}
          </p>
          {!planFilter && (
            <button className="btn btn-primary empty-state-action" onClick={openCreate}>Crear primer negocio</button>
          )}
        </div>
      ) : (
        <div className="table-card">
          <div className="table-responsive">
          <table className="data-table tenants-table">
            <thead>
              <tr>
                <th>Negocio</th>
                <th>Departamento</th>
                <th>Ciudad</th>
                <th>Teléfono</th>
                <th>Administrador</th>
                <th>Correo admin</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map(t => (
                <tr key={t.id}>
                  <td>
                    <span className="cell-main">{t.name}</span>
                    {t.slug && (
                      <div className="cell-muted">
                        <code className="slug-code">{t.slug}</code>
                      </div>
                    )}
                  </td>
                  <td className="cell-nowrap">{t.state_name || '—'}</td>
                  <td className="cell-nowrap">{t.city_name || t.city || '—'}</td>
                  <td className="cell-nowrap">{t.phone || '—'}</td>
                  <td className="cell-nowrap">{adminName(t)}</td>
                  <td>
                    <span className="cell-email">{adminEmail(t)}</span>
                  </td>
                  <td><span className={`badge badge-plan ${planBadgeClass(t)}`}>{planName(t)}</span></td>
                  <td>{statusBadge(t.is_active)}</td>
                  <td className="cell-actions">
                    <div className="table-actions">
                      <button className="btn btn-outline btn-sm" onClick={() => openEdit(t)}>
                        Editar
                      </button>
                      <button
                        className={`btn btn-sm ${t.is_active ? 'btn-danger' : 'btn-success'}`}
                        onClick={() => toggleActive(t)}
                      >
                        {t.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}

      {/* -- Modal Crear negocio ---------------------------- */}
      {modal === 'create' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Crear negocio con accesos</h3>
              <button className="modal-close" onClick={() => setModal(null)}>✕</button>
            </div>

            {feedback && (
              <div className="alert alert-error modal-alert">
                {feedback}
              </div>
            )}

            <form onSubmit={handleSubmitCreate} className="modal-form" noValidate>

              {/* -- Sección: Datos del negocio ----------- */}
              <div className="modal-section-header">Datos del negocio</div>

              <div className="form-row">
                <div className="form-group">
                  <label>Nombre comercial *</label>
                  <input
                    name="name"
                    value={tenantForm.name}
                    onChange={handleTenantChange}
                    placeholder="Barbería Ejemplo"
                    className={fieldErrors.name ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.name} />
                </div>
                <div className="form-group">
                  <label>Identificador público</label>
                  <div className={`slug-preview${tenantForm.slug ? '' : ' slug-preview--empty'}`}>
                    {tenantForm.slug || 'Se genera al escribir el nombre comercial'}
                  </div>
                  <small className="field-hint">Generado automáticamente a partir del nombre comercial.</small>
                </div>
              </div>

              <div className="form-group">
                <label>Descripción *</label>
                <input
                  name="description"
                  value={tenantForm.description}
                  onChange={handleTenantChange}
                  placeholder="Descripción del negocio"
                  className={fieldErrors.description ? 'input-error' : ''}
                />
                <FieldError msg={fieldErrors.description} />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Teléfono *</label>
                  <input
                    name="phone"
                    value={tenantForm.phone}
                    onChange={handleTenantChange}
                    placeholder="3001234567"
                    inputMode="numeric"
                    maxLength={10}
                    className={fieldErrors.phone ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.phone} />
                </div>
                <div className="form-group">
                  <label>Dirección *</label>
                  <input
                    name="address"
                    value={tenantForm.address}
                    onChange={handleTenantChange}
                    placeholder="Calle 45 # 12-30"
                    className={fieldErrors.address ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.address} />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Departamento *</label>
                  <select
                    name="state_id"
                    value={tenantForm.state_id}
                    onChange={handleTenantChange}
                    className={fieldErrors.state_id ? 'input-error' : ''}
                  >
                    <option value="">Selecciona un departamento</option>
                    {states.map(s => (
                      <option key={s.id} value={s.id}>{s.description}</option>
                    ))}
                  </select>
                  <FieldError msg={fieldErrors.state_id} />
                </div>
                <div className="form-group">
                  <label>Ciudad *</label>
                  <select
                    name="city_id"
                    value={tenantForm.city_id}
                    onChange={handleTenantChange}
                    disabled={!tenantForm.state_id}
                    className={fieldErrors.city ? 'input-error' : ''}
                  >
                    <option value="">
                      {tenantForm.state_id ? 'Selecciona una ciudad' : 'Primero selecciona un departamento'}
                    </option>
                    {cities.map(c => (
                      <option key={c.id} value={c.id}>{c.description}</option>
                    ))}
                  </select>
                  <FieldError msg={fieldErrors.city} />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Horario de apertura *</label>
                  <input
                    name="opening_time"
                    type="time"
                    value={tenantForm.opening_time}
                    onChange={handleTenantChange}
                    className={fieldErrors.opening_time ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.opening_time} />
                </div>
                <div className="form-group">
                  <label>Horario de cierre *</label>
                  <input
                    name="closing_time"
                    type="time"
                    value={tenantForm.closing_time}
                    onChange={handleTenantChange}
                    className={fieldErrors.closing_time ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.closing_time} />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Plan *</label>
                  <select
                    name="plan_id"
                    value={tenantForm.plan_id}
                    onChange={handleTenantChange}
                    className={fieldErrors.plan_id ? 'input-error' : ''}
                  >
                    <option value="">Selecciona un plan</option>
                    {plans.map(p => (
                      <option key={p.id} value={p.id}>{p.display_name}</option>
                    ))}
                  </select>
                  <FieldError msg={fieldErrors.plan_id} />
                </div>
                <div className="form-group form-group-end">
                  <div className="form-check form-check-bottom">
                    <input
                      type="checkbox"
                      id="is_active_create"
                      name="is_active"
                      checked={tenantForm.is_active}
                      onChange={handleTenantChange}
                    />
                    <label htmlFor="is_active_create">Negocio activo</label>
                  </div>
                </div>
              </div>

              {/* -- Sección: Accesos del administrador ---- */}
              <div className="modal-section-header modal-section-header-spaced">
                Accesos del administrador
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input
                    name="first_name"
                    value={adminForm.first_name}
                    onChange={handleAdminChange}
                    placeholder="Nombre"
                    className={fieldErrors.first_name ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.first_name} />
                </div>
                <div className="form-group">
                  <label>Apellido *</label>
                  <input
                    name="last_name"
                    value={adminForm.last_name}
                    onChange={handleAdminChange}
                    placeholder="Apellido"
                    className={fieldErrors.last_name ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.last_name} />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Correo electrónico *</label>
                  <input
                    type="email"
                    name="email"
                    value={adminForm.email}
                    onChange={handleAdminChange}
                    placeholder="admin@negocio.com"
                    className={fieldErrors.email ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.email} />
                </div>
                <div className="form-group">
                  <label>Teléfono del administrador</label>
                  <input
                    name="phone"
                    value={adminForm.phone}
                    onChange={handleAdminChange}
                    placeholder="3101234567"
                    inputMode="numeric"
                    maxLength={10}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Contraseña inicial *</label>
                  <input
                    type="password"
                    name="password"
                    value={adminForm.password}
                    onChange={handleAdminChange}
                    placeholder="Mínimo 8 caracteres"
                    className={fieldErrors.password ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.password} />
                </div>
                <div className="form-group">
                  <label>Confirmar contraseña *</label>
                  <input
                    type="password"
                    name="confirm_password"
                    value={adminForm.confirm_password}
                    onChange={handleAdminChange}
                    placeholder="Repetir contraseña"
                    className={fieldErrors.confirm_password ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.confirm_password} />
                </div>
              </div>

              <div className="alert alert-info alert-compact">
                El administrador podrá iniciar sesión con el correo y contraseña asignados.
                El rol <strong>tenant_admin</strong> se asigna automáticamente.
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Creando...' : 'Guardar negocio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* -- Modal Editar negocio --------------------------- */}
      {modal === 'edit' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Editar negocio</h3>
              <button className="modal-close" onClick={() => setModal(null)}>✕</button>
            </div>

            {feedback && (
              <div className="alert alert-error modal-alert">
                {feedback}
              </div>
            )}

            <form onSubmit={handleSubmitEdit} className="modal-form" noValidate>
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input
                    name="name"
                    value={tenantForm.name}
                    onChange={handleTenantChange}
                    className={fieldErrors.name ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.name} />
                </div>
                <div className="form-group">
                  <label>Identificador público</label>
                  <div className={`slug-preview${tenantForm.slug ? '' : ' slug-preview--empty'}`}>
                    {tenantForm.slug || 'Se genera automáticamente'}
                  </div>
                  <FieldError msg={fieldErrors.slug} />
                </div>
              </div>

              <div className="form-group">
                <label>Descripción</label>
                <input name="description" value={tenantForm.description} onChange={handleTenantChange} />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Teléfono *</label>
                  <input
                    name="phone"
                    value={tenantForm.phone}
                    onChange={handleTenantChange}
                    placeholder="3001234567"
                    inputMode="numeric"
                    maxLength={10}
                    className={fieldErrors.phone ? 'input-error' : ''}
                  />
                  <FieldError msg={fieldErrors.phone} />
                </div>
                <div className="form-group">
                  <label>Departamento</label>
                  <select
                    name="state_id"
                    value={tenantForm.state_id}
                    onChange={handleTenantChange}
                  >
                    <option value="">Selecciona un departamento</option>
                    {states.map(s => (
                      <option key={s.id} value={s.id}>{s.description}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Ciudad</label>
                <select
                  name="city_id"
                  value={tenantForm.city_id}
                  onChange={handleTenantChange}
                  disabled={!tenantForm.state_id}
                >
                  <option value="">
                    {tenantForm.state_id ? 'Selecciona una ciudad' : 'Primero selecciona un departamento'}
                  </option>
                  {cities.map(c => (
                    <option key={c.id} value={c.id}>{c.description}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Dirección</label>
                <input name="address" value={tenantForm.address} onChange={handleTenantChange} />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Apertura</label>
                  <input name="opening_time" type="time" value={tenantForm.opening_time} onChange={handleTenantChange} />
                </div>
                <div className="form-group">
                  <label>Cierre</label>
                  <input name="closing_time" type="time" value={tenantForm.closing_time} onChange={handleTenantChange} />
                </div>
              </div>

              <div className="form-group">
                <label>Plan</label>
                <select name="plan_id" value={tenantForm.plan_id} onChange={handleTenantChange}>
                  <option value="">Sin plan asignado</option>
                  {plans.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
                </select>
              </div>

              <div className="form-group form-check">
                <input
                  type="checkbox"
                  id="is_active_edit"
                  name="is_active"
                  checked={tenantForm.is_active}
                  onChange={handleTenantChange}
                />
                <label htmlFor="is_active_edit">Negocio activo</label>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setModal(null)}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Guardando...' : 'Actualizar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
