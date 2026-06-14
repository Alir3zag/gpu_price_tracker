export const formatPrice = (price, currency = 'USD') => {
  if (price == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price)
}

export const formatPercent = (val) => {
  if (val == null) return '—'
  return `${val > 0 ? '-' : ''}${Math.abs(val).toFixed(1)}%`
}

export const formatDate = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export const formatDateShort = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  })
}

export const gradeColor = (grade) => {
  const map = { A: 'var(--grade-a)', B: 'var(--grade-b)', C: 'var(--grade-c)', D: 'var(--grade-d)' }
  return map[grade] || 'var(--text-muted)'
}

export const gradeBg = (grade) => {
  const map = { A: 'var(--grade-a-dim)', B: 'var(--grade-b-dim)', C: 'var(--grade-c-dim)', D: 'var(--grade-d-dim)' }
  return map[grade] || 'transparent'
}

export const capitalize = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
