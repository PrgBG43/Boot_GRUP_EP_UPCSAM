export function groupByBusiness(items, businesses = []) {
  const businessNames = new Map((businesses || []).map(business => [business.id, business.name]))
  const groups = new Map()

  for (const item of items || []) {
    const tenantId = item.tenant_id ?? 'unknown'
    const tenantName = item.tenant_name || businessNames.get(item.tenant_id) || `Negocio #${tenantId}`
    if (!groups.has(tenantId)) {
      groups.set(tenantId, { tenantId, tenantName, items: [] })
    }
    groups.get(tenantId).items.push(item)
  }

  return [...groups.values()].sort((a, b) => a.tenantName.localeCompare(b.tenantName, 'es'))
}
