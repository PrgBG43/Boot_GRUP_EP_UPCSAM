import { useEffect, useMemo, useState } from 'react'

const groupKey = group => String(group.tenantId ?? group.id ?? group.tenantName)

export default function BusinessAccordion({
  groups,
  itemLabel,
  renderGroup,
  emptyTitle,
  emptyText,
}) {
  const [openGroups, setOpenGroups] = useState(() => new Set())
  const keys = useMemo(() => groups.map(groupKey).join('|'), [groups])

  useEffect(() => {
    setOpenGroups(prev => {
      const validKeys = new Set(groups.map(groupKey))
      return new Set([...prev].filter(key => validKeys.has(key)))
    })
  }, [keys]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleGroup = key => {
    setOpenGroups(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  if (groups.length === 0) {
    return (
      <div className="empty-state">
        <h2 className="empty-state-title">{emptyTitle}</h2>
        <p className="empty-state-text">{emptyText}</p>
      </div>
    )
  }

  return (
    <div className="business-accordion">
      {groups.map(group => {
        const key = groupKey(group)
        const isOpen = openGroups.has(key)
        return (
          <section className={`business-group${isOpen ? ' is-open' : ''}`} key={key}>
            <button
              type="button"
              className="business-group-header"
              onClick={() => toggleGroup(key)}
              aria-expanded={isOpen}
            >
              <span className="business-group-toggle" aria-hidden="true">{isOpen ? '-' : '+'}</span>
              <span className="business-group-title-wrap">
                <span className="business-group-title">{group.tenantName}</span>
                {group.internalCode && <span className="business-group-code">Código interno: {group.internalCode}</span>}
              </span>
              <span className="business-group-count">
                {group.items.length} {group.items.length === 1 ? itemLabel.singular : itemLabel.plural}
              </span>
            </button>
            {isOpen && (
              <div className="business-group-body">
                {renderGroup(group)}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}
