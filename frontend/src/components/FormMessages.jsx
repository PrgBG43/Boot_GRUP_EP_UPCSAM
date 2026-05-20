export function FieldError({ msg }) {
  if (!msg) return null
  return <span className="field-error">{msg}</span>
}

export function FormError({ children }) {
  if (!children) return null
  return <div className="alert alert-error form-alert">{children}</div>
}

export function AlertMessage({ type = 'info', children }) {
  if (!children) return null
  return <div className={`alert alert-${type}`}>{children}</div>
}
