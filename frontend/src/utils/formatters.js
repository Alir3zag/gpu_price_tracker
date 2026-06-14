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

// Extract a short, human-readable GPU model name from a full product title
// e.g. "ASUS TUF Gaming GeForce RTX 4090 24GB GDDR6X PCIe 4.0..." → "RTX 4090 TUF Gaming"
export const shortGPUName = (name) => {
  if (!name) return '—'

  // Extract GPU model number
  const modelMatch = name.match(/(?:RTX|GTX|RX|Arc)\s*\d{3,4}(?:\s*Ti|\s*XT|\s*XTX|\s*SUPER)?/i)
  const model = modelMatch ? modelMatch[0].replace(/\s+/g, ' ').trim() : null

  // Extract brand qualifier (ROG Strix, TUF Gaming, AORUS, SUPRIM, etc.)
  const qualifiers = [
    'ROG Strix', 'ROG STRIX', 'TUF Gaming', 'AORUS', 'SUPRIM', 'Ventus',
    'Gaming X', 'Gaming OC', 'GAMING OC', 'Founders Edition', 'FTW3',
    'WINDFORCE', 'Eagle', 'Vision', 'VERTO', 'Trinity',
  ]
  let qualifier = null
  for (const q of qualifiers) {
    if (name.includes(q)) { qualifier = q; break }
  }

  // OC / White / Master suffix
  const suffixes = []
  if (/\bWhite\b/i.test(name)) suffixes.push('White')
  if (/\bOC\b|\bO\d+G\b/i.test(name)) suffixes.push('OC')
  if (/\bMaster\b/i.test(name)) suffixes.push('Master')
  if (/\bXTREME\b/i.test(name)) suffixes.push('Xtreme')
  if (/\bWATERFORCE\b/i.test(name)) suffixes.push('WF')
  if (/\bRefurbished\b/i.test(name)) suffixes.push('Refurb')

  if (model) {
    const parts = [model]
    if (qualifier) parts.push(qualifier)
    parts.push(...suffixes)
    return parts.join(' ').slice(0, 40)
  }

  // Fallback: strip filler and truncate
  return name
    .replace(/GeForce\s*/gi, '')
    .replace(/Graphics Card.*/gi, '')
    .replace(/Video Card.*/gi, '')
    .replace(/PCI Express.*$/gi, '')
    .replace(/GDDR\d+X?\s*\d*GB/gi, '')
    .replace(/\d+GB\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 40)
}
