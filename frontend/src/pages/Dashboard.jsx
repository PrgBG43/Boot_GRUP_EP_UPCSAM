import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '../context/AuthContext.jsx'
import api from '../api.js'
import { planLabel, statusBadgeClass, statusLabel } from '../utils/labels.js'
import './Dashboard.css'

const COLORS = ['#6c3fc5', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#64748b', '#ec4899', '#14b8a6']

function asCurrency(value) {
  return `$${Number(value || 0).toLocaleString('es-CO')}`
}

function chartData(items = [], labelKey, valueKey, labelMapper = value => value) {
  return items.map(item => ({
    ...item,
    label: labelMapper(item[labelKey]),
    value: Number(item[valueKey] || item.value || 0),
  }))
}

function StatCard({ label, value, sub, color = '#6c3fc5' }) {
  return (
    <div className="stat-card" style={{ borderTop: `3px solid ${color}` }}>
      <div className="stat-body">
        <div className="stat-value">{value ?? '0'}</div>
        <div className="stat-label">{label}</div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  )
}

function ChartCard({ title, children, empty }) {
  return (
    <div className="card analytics-card">
      <h2 className="card-title">{title}</h2>
      {empty ? <div className="empty-state-sm">Sin datos para mostrar</div> : <div className="chart-box">{children}</div>}
    </div>
  )
}

function Insights({ items = [] }) {
  return (
    <div className="card analytics-insights">
      <h2 className="card-title">Análisis</h2>
      {items.length === 0 ? (
        <div className="empty-state-sm">Sin análisis disponible</div>
      ) : (
        <div className="insight-list">
          {items.map((item, index) => <div className="insight-item" key={`${item}-${index}`}>{item}</div>)}
        </div>
      )}
    </div>
  )
}

function AnalyticsFilters({ children, onClear }) {
  return (
    <div className="page-toolbar dashboard-filters">
      <div className="dashboard-filter-controls">{children}</div>
      <div className="action-group">
        <button type="button" className="btn btn-outline" onClick={onClear}>Limpiar filtros</button>
      </div>
    </div>
  )
}

function DashboardFilterItem({ id, label, children, className = '' }) {
  return (
    <label className={`dashboard-filter-item ${className}`.trim()} htmlFor={id}>
      <span className="filter-label">{label}</span>
      {children}
    </label>
  )
}

function DateFilterField({ id, label, value, onChange }) {
  return (
    <DashboardFilterItem id={id} label={label} className="dashboard-filter-item--date">
      <input id={id} className="filter-select filter-control" type="date" value={value} onChange={event => onChange(event.target.value)} />
    </DashboardFilterItem>
  )
}

function SelectFilterField({ id, label, value, onChange, children }) {
  return (
    <DashboardFilterItem id={id} label={label}>
      <select id={id} className="filter-select filter-control" value={value} onChange={event => onChange(event.target.value)}>
        {children}
      </select>
    </DashboardFilterItem>
  )
}

function TextFilterField({ id, label, value, onChange, placeholder }) {
  return (
    <DashboardFilterItem id={id} label={label}>
      <input id={id} className="search-input filter-control" placeholder={placeholder} value={value} onChange={event => onChange(event.target.value)} />
    </DashboardFilterItem>
  )
}

function FilterPlaceholder({ value, children }) {
  return (
    <option value={value}>{children}</option>
  )
}

function PlanFilter({ value, onChange }) {
  return (
    <SelectFilterField id="dashboard-global-plan" label="Plan" value={value} onChange={onChange}>
      <FilterPlaceholder value="">Todos los planes</FilterPlaceholder>
      <option value="free">Gratuito</option>
      <option value="premium">Premium</option>
    </SelectFilterField>
  )
}

function BusinessStatusFilter({ value, onChange }) {
  return (
    <SelectFilterField id="dashboard-global-status" label="Estado" value={value} onChange={onChange}>
      <FilterPlaceholder value="">Todos los estados</FilterPlaceholder>
      <option value="active">Activos</option>
      <option value="inactive">Inactivos</option>
      <option value="archived">Archivados</option>
    </SelectFilterField>
  )
}

function AppointmentStatusFilter({ id, value, onChange }) {
  return (
    <SelectFilterField id={id} label="Estado" value={value} onChange={onChange}>
      <FilterPlaceholder value="">Todos los estados</FilterPlaceholder>
      <option value="pending">Pendiente</option>
      <option value="confirmed">Confirmada</option>
      <option value="completed">Completada</option>
      <option value="cancelled">Cancelada</option>
    </SelectFilterField>
  )
}

function TenantFilter({ value, onChange, businesses }) {
  return (
    <SelectFilterField id="dashboard-global-tenant" label="Negocio" value={value} onChange={onChange}>
      <FilterPlaceholder value="">Todos los negocios</FilterPlaceholder>
      {businesses.map(business => <option key={business.id} value={business.id}>{business.name}</option>)}
    </SelectFilterField>
  )
}

function CityFilter({ value, onChange }) {
  return (
    <TextFilterField
      id="dashboard-global-city"
      label="Ciudad"
      placeholder="Filtrar por ciudad..."
      value={value}
      onChange={onChange}
    />
  )
}

function GlobalDashboardFilters({ filters, setFilter, businesses, clearFilters }) {
  return (
    <AnalyticsFilters onClear={clearFilters}>
      <DateFilterField id="dashboard-global-date-from" label="Desde" value={filters.date_from} onChange={value => setFilter('date_from', value)} />
      <DateFilterField id="dashboard-global-date-to" label="Hasta" value={filters.date_to} onChange={value => setFilter('date_to', value)} />
      <PlanFilter value={filters.plan} onChange={value => setFilter('plan', value)} />
      <BusinessStatusFilter value={filters.status} onChange={value => setFilter('status', value)} />
      <CityFilter value={filters.city} onChange={value => setFilter('city', value)} />
      <TenantFilter value={filters.tenant_id} onChange={value => setFilter('tenant_id', value)} businesses={businesses} />
    </AnalyticsFilters>
  )
}

function TenantDashboardFilters({ filters, setFilter, clearFilters }) {
  return (
    <AnalyticsFilters onClear={clearFilters}>
      <DateFilterField id="dashboard-tenant-date-from" label="Desde" value={filters.date_from} onChange={value => setFilter('date_from', value)} />
      <DateFilterField id="dashboard-tenant-date-to" label="Hasta" value={filters.date_to} onChange={value => setFilter('date_to', value)} />
      <AppointmentStatusFilter id="dashboard-tenant-status" value={filters.status} onChange={value => setFilter('status', value)} />
    </AnalyticsFilters>
  )
}

function SuperadminDashboard() {
  const { activeTenantId } = useAuth()
  const [data, setData] = useState(null)
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [filters, setFilters] = useState({ date_from: '', date_to: '', plan: '', status: '', city: '', tenant_id: activeTenantId || '' })

  useEffect(() => {
    setFilters(current => ({ ...current, tenant_id: activeTenantId || '' }))
  }, [activeTenantId])

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      Object.entries(filters).forEach(([key, value]) => { if (value) params[key] = value })
      const [dashboard, businessData] = await Promise.all([
        api.getSuperadminDashboard(params),
        api.getBusinesses({ page_size: 100 }),
      ])
      setData(dashboard)
      setBusinesses(businessData?.items || businessData || [])
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err.message || 'No fue posible cargar el dashboard.')
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [filters]) // eslint-disable-line react-hooks/exhaustive-deps

  const setFilter = (key, value) => setFilters(current => ({ ...current, [key]: value }))
  const clearFilters = () => setFilters({ date_from: '', date_to: '', plan: '', status: '', city: '', tenant_id: activeTenantId || '' })

  if (loading && !data) return <div className="spinner" />
  if (error) return <div className="alert alert-error">Error: {error}</div>

  const summary = data?.summary || {}
  const charts = data?.charts || {}
  const appointmentMonths = chartData(charts.appointments_by_month, 'month', 'appointments')
  const statusRows = chartData(charts.appointments_by_status, 'status', 'count', statusLabel)
  const planRows = chartData(charts.businesses_by_plan, 'label', 'count')
  const topBusinesses = chartData(charts.top_businesses, 'name', 'appointments')
  const clientsByMonth = chartData(charts.clients_by_month, 'month', 'clients')
  const conversationsByMonth = chartData(charts.conversations_by_month, 'month', 'conversations')
  const appointmentsByCity = chartData(charts.appointments_by_city, 'city', 'appointments')
  const growthRows = chartData(charts.business_growth, 'month', 'businesses')
  const ticketStatusRows = chartData(charts.support_tickets_by_status, 'status', 'count', statusLabel)
  const ticketPriorityRows = chartData(charts.support_tickets_by_priority, 'priority', 'count', statusLabel)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Panel de Plataforma</h1>
          <p>Vista analítica global de Turnix</p>
        </div>
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
        </div>
      </div>

      <GlobalDashboardFilters
        filters={filters}
        setFilter={setFilter}
        businesses={businesses}
        clearFilters={clearFilters}
      />

      <div className="stats-grid">
        <StatCard label="Negocios totales" value={summary.total_businesses} />
        <StatCard label="Negocios activos" value={summary.active_businesses} color="#10b981" />
        <StatCard label="Archivados o inactivos" value={(summary.archived_businesses || 0) + (summary.inactive_businesses || 0)} color="#64748b" />
        <StatCard label="Negocios Gratuitos" value={summary.free_businesses} color="#0ea5e9" />
        <StatCard label="Negocios Premium" value={summary.premium_businesses} color="#8b5cf6" />
        <StatCard label="Citas del mes" value={summary.monthly_appointments} color="#f59e0b" />
        <StatCard label="Clientes registrados" value={summary.total_clients} color="#14b8a6" />
        <StatCard label="Conversaciones Telegram" value={summary.total_conversations} color="#ec4899" />
        <StatCard label="Cerca del límite" value={summary.near_limit_businesses} color="#f59e0b" />
        <StatCard label="Límite alcanzado" value={summary.limit_reached_businesses} color="#ef4444" />
        <StatCard label="Tickets abiertos" value={summary.open_tickets} color="#10b981" />
        <StatCard label="Tickets urgentes" value={summary.urgent_tickets} color="#ef4444" />
        <StatCard label="Tickets Premium" value={summary.premium_tickets} color="#8b5cf6" />
      </div>

      <Insights items={data?.insights || []} />

      <div className="analytics-grid">
        <ChartCard title="Citas por mes" empty={appointmentMonths.every(item => item.value === 0)}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={appointmentMonths}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" name="Citas" stroke="#6c3fc5" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Citas por estado" empty={statusRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={statusRows} dataKey="value" nameKey="label" outerRadius={88} label>
                {statusRows.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Negocios por plan" empty={planRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={planRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Negocios" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Negocios más activos" empty={topBusinesses.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={topBusinesses} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="label" width={110} />
              <Tooltip />
              <Bar dataKey="value" name="Citas" fill="#10b981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Clientes registrados por mes" empty={clientsByMonth.every(item => item.value === 0)}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={clientsByMonth}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Clientes" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Conversaciones por mes" empty={conversationsByMonth.every(item => item.value === 0)}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={conversationsByMonth}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" name="Conversaciones" stroke="#ec4899" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Citas por ciudad" empty={appointmentsByCity.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={appointmentsByCity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Citas" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Crecimiento de negocios" empty={growthRows.every(item => item.value === 0)}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={growthRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" name="Negocios" stroke="#64748b" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Tickets por estado" empty={ticketStatusRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={ticketStatusRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Tickets" fill="#6c3fc5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Tickets por prioridad" empty={ticketPriorityRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={ticketPriorityRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Tickets" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}

function TenantDashboard() {
  const { user, isSuperadmin, activeTenantId } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [filters, setFilters] = useState({ date_from: '', date_to: '', status: '' })

  const tenantId = isSuperadmin ? activeTenantId : null

  const load = async () => {
    if (isSuperadmin && !tenantId) {
      setLoading(false)
      setData(null)
      return
    }
    setLoading(true)
    try {
      const params = {}
      Object.entries(filters).forEach(([key, value]) => { if (value) params[key] = value })
      const dashboard = await api.getTenantDashboard(tenantId, params)
      setData(dashboard)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err.message || 'No fue posible cargar el dashboard.')
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [tenantId, filters]) // eslint-disable-line react-hooks/exhaustive-deps

  const setFilter = (key, value) => setFilters(current => ({ ...current, [key]: value }))
  const clearFilters = () => setFilters({ date_from: '', date_to: '', status: '' })

  if (loading && !data) return <div className="spinner" />
  if (error) return <div className="alert alert-error">Error: {error}</div>
  if (!data) {
    return (
      <div className="empty-state">
        <h2 className="empty-state-title">Selecciona un negocio</h2>
        <p className="empty-state-text">Selecciona un negocio en el menú lateral para ver sus métricas.</p>
      </div>
    )
  }

  const summary = data.summary || {}
  const charts = data.charts || {}
  const appointmentsByDay = chartData(charts.appointments_by_day, 'date', 'appointments')
  const statusRows = chartData(charts.appointments_by_status, 'status', 'count', statusLabel)
  const topServices = chartData(charts.top_services, 'name', 'appointments')
  const conversationsByDay = chartData(charts.conversations_by_day, 'date', 'conversations')
  const demandRows = chartData(charts.demand_by_hour, 'hour', 'appointments')
  const revenueRows = chartData(charts.revenue_by_service, 'name', 'revenue')
  const planRows = chartData(charts.plan_usage, 'name', 'value')
  const planUsage = data.plan_usage || {}

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>{data.tenant?.name || user?.tenant_name || 'Resumen del negocio'}</p>
        </div>
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
        </div>
      </div>

      <TenantDashboardFilters filters={filters} setFilter={setFilter} clearFilters={clearFilters} />

      <div className="stats-grid">
        <StatCard label="Citas del mes" value={summary.appointments_in_range} />
        <StatCard label="Citas de hoy" value={summary.appointments_today} color="#0ea5e9" />
        <StatCard label="Pendientes" value={summary.pending_appointments} color="#f59e0b" />
        <StatCard label="Confirmadas" value={summary.confirmed_appointments} color="#10b981" />
        <StatCard label="Completadas" value={summary.completed_appointments} color="#64748b" />
        <StatCard label="Canceladas" value={summary.cancelled_appointments} color="#ef4444" />
        <StatCard label="Clientes registrados" value={summary.clients_registered} color="#14b8a6" />
        <StatCard label="Conversaciones recibidas" value={summary.conversations_received} color="#ec4899" />
        <StatCard label="Tickets abiertos" value={summary.open_tickets} color="#f59e0b" />
        <StatCard
          label="Uso del plan"
          value={summary.plan_limit ? `${summary.plan_used} / ${summary.plan_limit}` : 'Ilimitado'}
          sub={summary.plan_limit ? `${summary.plan_remaining} citas restantes` : planLabel(data.tenant?.plan)}
          color="#8b5cf6"
        />
        <StatCard label="Ingresos estimados" value={asCurrency(summary.estimated_income)} color="#10b981" />
      </div>

      {planUsage?.near_limit && (
        <div className="alert alert-warning">Estás cerca de alcanzar el límite mensual de tu plan.</div>
      )}
      {planUsage?.limit_reached && (
        <div className="alert alert-error">Alcanzaste el límite mensual de tu plan.</div>
      )}

      <Insights items={data.insights || []} />

      <div className="analytics-grid">
        <ChartCard title="Citas por día" empty={appointmentsByDay.every(item => item.value === 0)}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={appointmentsByDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" name="Citas" stroke="#6c3fc5" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Citas por estado" empty={statusRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={statusRows} dataKey="value" nameKey="label" outerRadius={88} label>
                {statusRows.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Servicios más solicitados" empty={topServices.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={topServices}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Citas" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Horarios con más demanda" empty={demandRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={demandRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value" name="Citas" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Conversaciones por día" empty={conversationsByDay.every(item => item.value === 0)}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={conversationsByDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="value" name="Conversaciones" stroke="#ec4899" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Ingresos estimados por servicio" empty={revenueRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={revenueRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" />
              <YAxis />
              <Tooltip formatter={value => asCurrency(value)} />
              <Bar dataKey="value" name="Ingresos" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Uso mensual del plan" empty={planRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={planRows} dataKey="value" nameKey="label" outerRadius={88} label>
                {planRows.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}

function StaffDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const dashboard = await api.getStaffDashboard()
      setData(dashboard)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err.message || 'No fue posible cargar la agenda.')
    }
    setLoading(false)
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [])

  if (loading && !data) return <div className="spinner" />
  if (error) return <div className="alert alert-error">Error: {error}</div>

  const summary = data?.summary || {}
  const statusRows = chartData(data?.charts?.appointments_by_status, 'status', 'count', statusLabel)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Mi agenda</h1>
          <p>Resumen operativo del día</p>
        </div>
        <div className="header-actions">
          {lastUpdated && <span className="refresh-label">Actualizado hace unos segundos</span>}
          <button className="btn btn-outline" onClick={load}>Actualizar</button>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Citas de hoy" value={summary.appointments_today} />
        <StatCard label="Próximas citas" value={summary.upcoming_appointments} color="#0ea5e9" />
        <StatCard label="Completadas" value={summary.completed_appointments} color="#10b981" />
        <StatCard label="Pendientes" value={summary.pending_appointments} color="#f59e0b" />
        <StatCard label="Clientes atendidos" value={summary.clients_served} color="#14b8a6" />
      </div>

      <Insights items={data?.insights || []} />

      <div className="analytics-grid">
        <ChartCard title="Citas por estado" empty={statusRows.length === 0}>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={statusRows} dataKey="value" nameKey="label" outerRadius={88} label>
                {statusRows.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="card section-spacing">
        <h2 className="card-title">Próximas citas</h2>
        {(data?.upcoming_appointments || []).length === 0 ? (
          <div className="empty-state-sm">No hay citas próximas.</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table dashboard-table">
              <thead><tr><th>Fecha</th><th>Hora</th><th>Estado</th></tr></thead>
              <tbody>
                {data.upcoming_appointments.map(item => (
                  <tr key={item.id}>
                    <td className="cell-nowrap">{item.date}</td>
                    <td className="cell-nowrap">{item.start_time?.slice(0, 5)}</td>
                    <td><span className={`badge ${statusBadgeClass(item.status)}`}>{statusLabel(item.status)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { isSuperadmin, isStaff } = useAuth()
  if (isStaff) return <StaffDashboard />
  if (isSuperadmin) return <SuperadminDashboard />
  return <TenantDashboard />
}
