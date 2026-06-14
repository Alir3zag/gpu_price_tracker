import { useState, useEffect, useCallback } from 'react'
import { getAlerts } from '../api/alerts'
import GradeBadge from '../components/GradeBadge'
import { SkeletonRow } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { formatPrice, formatDate } from '../utils/formatters'

const GRADE_OPTS = ['All', 'A', 'B', 'C', 'D']
const RETAILER_OPTS = ['All', 'newegg', 'walmart', 'amazon', 'ebay']

function shortName(name) {
  if (!name) return '—'
  return name.replace(/PCI Express \d+\.\d+/gi, '').replace(/\s+/g, ' ').trim().slice(0, 55)
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [grade, setGrade] = useState('All')
  const [retailer, setRetailer] = useState('All')
  const toast = useToast()

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getAlerts({ limit: 200 })
      setAlerts(data)
    } catch {
      toast.error('Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAlerts() }, [loadAlerts])

  const filtered = alerts.filter(a => {
    if (grade !== 'All' && a.grade !== grade) return false
    if (retailer !== 'All' && a.retailer !== retailer) return false
    return true
  })

  const thisWeek = alerts.filter(a => {
    if (!a.created_at) return false
    return Date.now() - new Date(a.created_at).getTime() < 7 * 24 * 60 * 60 * 1000
  }).length

  const bestDeal = alerts.length
    ? alerts.reduce((b, a) => (a.score > b.score ? a : b), alerts[0])
    : null

  const avgDrop = alerts.length
    ? (alerts.reduce((s, a) => s + (a.drop_pct || 0), 0) / alerts.length).toFixed(1)
    : null

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Alerts</h1>
        {/* Grade legend */}
        <div style={{ display: 'flex', gap: 12, fontSize: 11 }}>
          {[['A', 'var(--grade-a)', '80+'], ['B', 'var(--grade-b)', '60+'], ['C', 'var(--grade-c)', '40+'], ['D', 'var(--grade-d)', '0+']].map(([g, color, range]) => (
            <span key={g} style={{ color, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block' }} />
              Grade {g} · {range}
            </span>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'This Week', value: loading ? '—' : thisWeek },
          { label: 'Total Alerts', value: loading ? '—' : alerts.length },
          { label: 'Best Score', value: loading || !bestDeal ? '—' : Math.round(bestDeal.score), accent: 'var(--accent)' },
          { label: 'Avg Drop', value: loading || !avgDrop ? '—' : `${avgDrop}%` },
        ].map(({ label, value, accent }) => (
          <div key={label} className="card" style={{ padding: '14px 18px', flex: 1 }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>
              {label}
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 600, color: accent || 'var(--text-primary)' }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        {/* Filters */}
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid var(--border)',
          display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
        }}>
          <select value={grade} onChange={e => setGrade(e.target.value)}>
            {GRADE_OPTS.map(g => <option key={g} value={g}>{g === 'All' ? 'All grades' : `Grade ${g}`}</option>)}
          </select>
          <select value={retailer} onChange={e => setRetailer(e.target.value)}>
            {RETAILER_OPTS.map(r => <option key={r} value={r}>{r === 'All' ? 'All retailers' : r}</option>)}
          </select>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: '35%' }}>GPU</th>
                <th>Retailer</th>
                <th>Old</th>
                <th>New</th>
                <th>Drop</th>
                <th>Grade</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={8} />)
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40, fontSize: 13 }}>
                    {alerts.length === 0
                      ? 'No alerts yet — run a scrape to start tracking deals.'
                      : 'No alerts match your filters.'}
                  </td>
                </tr>
              ) : (
                filtered.map(a => (
                  <tr key={a.id}>
                    <td title={a.gpu_name}>
                      <div style={{
                        fontWeight: 500, fontSize: 12,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        maxWidth: 260,
                      }}>
                        {shortName(a.gpu_name)}
                      </div>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                      {a.retailer || '—'}
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)', textDecoration: 'line-through' }}>
                        {formatPrice(a.old_price)}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 13, fontWeight: 700 }}>
                        {formatPrice(a.new_price)}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ color: 'var(--grade-a)', fontWeight: 700, fontSize: 13 }}>
                        -{a.drop_pct?.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <GradeBadge grade={a.grade} pulse={a.grade === 'A'} />
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {formatDate(a.created_at)}
                    </td>
                    <td>
                      {a.link && (
                        <a
                          href={a.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '4px 10px',
                            background: 'var(--accent-dim)',
                            border: '1px solid rgba(245,166,35,0.3)',
                            color: 'var(--accent)',
                            borderRadius: 5,
                            fontSize: 11,
                            fontWeight: 600,
                            textDecoration: 'none',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          View ↗
                        </a>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
