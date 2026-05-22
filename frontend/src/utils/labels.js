const STATUS_LABELS = {
  active: 'Activo',
  inactive: 'Inactivo',
  archived: 'Archivado',
  deleted: 'Eliminado',
  pending: 'Pendiente',
  confirmed: 'Confirmada',
  completed: 'Completada',
  cancelled: 'Cancelada',
  canceled: 'Cancelada',
  no_show: 'No asistió',
  scheduled: 'Programada',
  open: 'Abierta',
  closed: 'Cerrada',
  connected: 'Conectado',
  not_connected: 'No conectado',
  token_invalid: 'Token inválido',
  error: 'Error',
}

const STATUS_BADGES = {
  active: 'badge-success',
  connected: 'badge-success',
  confirmed: 'badge-success',
  completed: 'badge-neutral',
  inactive: 'badge-neutral',
  archived: 'badge-neutral',
  closed: 'badge-neutral',
  cancelled: 'badge-danger',
  canceled: 'badge-danger',
  deleted: 'badge-danger',
  token_invalid: 'badge-danger',
  error: 'badge-danger',
  pending: 'badge-warning',
  scheduled: 'badge-warning',
  open: 'badge-success',
  not_connected: 'badge-warning',
  no_show: 'badge-neutral',
}

const ROLE_LABELS = {
  superadmin: 'Superadministrador',
  tenant_admin: 'Administrador del negocio',
  staff: 'Personal',
  customer: 'Cliente',
}

const ROLE_BADGES = {
  superadmin: 'role-superadmin',
  tenant_admin: 'role-admin',
  staff: 'role-staff',
  customer: 'role-customer',
}

const CHANNEL_LABELS = {
  telegram: 'Telegram',
}

const BOT_STEP_LABELS = {
  ORIENTATION: 'Orientación',
  START: 'Inicio',
  SELECT_SERVICE: 'Selección de servicio',
  SELECT_DATE: 'Selección de fecha',
  SELECT_TIME: 'Selección de hora',
  ASK_NAME: 'Solicitud de nombre',
  ASK_PHONE: 'Solicitud de teléfono',
  CONFIRM_APPOINTMENT: 'Confirmación de cita',
  COMPLETED: 'Completado',
  CANCELLED: 'Cancelado',
  SERVICES_SHOWN: 'Servicios mostrados',
  SCHEDULE_SHOWN: 'Horarios mostrados',
  HELP_SHOWN: 'Ayuda mostrada',
  UNKNOWN_COMMAND: 'Comando no reconocido',
  UNKNOWN_CALLBACK: 'Acción no reconocida',
  CUSTOM_COMMAND: 'Respuesta personalizada',
  NO_AVAILABILITY: 'Sin disponibilidad',
  PLAN_LIMIT_REACHED: 'Agenda no disponible',
}

const PLAN_LABELS = {
  free: 'Gratuito',
  gratuito: 'Gratuito',
  premium: 'Premium',
}

function humanize(value) {
  if (value === null || value === undefined || value === '') return 'Sin definir'
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
    .replace(/^\w/, letter => letter.toUpperCase())
}

export function statusLabel(value) {
  return STATUS_LABELS[value] || humanize(value)
}

export function statusBadgeClass(value) {
  return STATUS_BADGES[value] || 'badge-neutral'
}

export function roleLabel(value) {
  return ROLE_LABELS[value] || humanize(value)
}

export function roleBadgeClass(value) {
  return ROLE_BADGES[value] || ''
}

export function channelLabel(value) {
  return CHANNEL_LABELS[value] || humanize(value)
}

export function botStepLabel(value) {
  if (!value) return '-'
  return BOT_STEP_LABELS[value] || humanize(value)
}

export function planLabel(value) {
  if (!value) return 'Sin plan'
  return PLAN_LABELS[String(value).toLowerCase()] || humanize(value)
}

export const ROLE_OPTIONS = Object.keys(ROLE_LABELS).map(value => ({
  value,
  label: ROLE_LABELS[value],
}))
