import { useState, useEffect, useCallback } from 'react'
import { getAlerts } from '../api/alerts'
import GradeBadge from '../components/GradeBadge'
import { SkeletonRow, SkeletonCard } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { formatPrice, formatDate } from '../utils/formatters'

const GRADE_OPTS = ['All', 'A', 'B', 'C', 'D']
const RETAILER_OPTS = ['All', 'newegg', 'walmart', 'amazon', 'ebay']

function StatPill({ label, value, color }) {
  return (
    <div className="card" style={{ padding: '14px 20px', flex: 1 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 600, color: color || 'var(--text-primary)' }}>
        {value}
      </div>
    </div>
  )
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
      const params = { limit: 200 }
      const { data } = await getAlerts(params)
      setAlerts(data)
    } catch {
      toast.error('Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAlerts() }, [loadAlerts])

  // Client-side filter
  const filtered = alerts.filter(a => {
    if (grade !== 'All' && a.grade !== grade) return false
    if (retailer !== 'All' && a.retailer !== retailer) return false
    return true
  })

  // Summary stats
  const thisWeek = alerts.filter(a => {
    if (!a.created_at) return false
    const d = new Date(a.created_at)
    return Date.now() - d.getTime() < 7 * 24 * 60 * 60 * 1000
  }).length

  const bestDeal = alerts.length ? alerts.reduce((best, a) => (a.score > best.score ? a : best), alerts[0]) : null
  const avgDrop = alerts.length ? (alerts.reduce((s, a) => s + (a.drop_pct || 0), 0) / alerts.length).toFixed(1) : '—'

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Alerts</h1>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          All detected price drops, sorted by deal quality
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
        <StatPill label="Alerts This Week" value={loading ? '—' : thisWeek} />
        <StatPill
          label="Best Deal (Score)"
          value={loading || !bestDeal ? '—' : `${Math.round(bestDeal.score)}`}
          color="var(--accent)"
        />
        <StatPill label="Avg Drop %" value={loading ? '—' : `${avgDrop}%`} />
        <StatPill label="Total Alerts" value={loading ? '—' : alerts.length} />
      </div>

      <div className="card">
        {/* Filters */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Filter:</div>
          <select value={grade} onChange={e => setGrade(e.target.value)}>
            {GRADE_OPTS.map(g => <option key={g}>{g === 'All' ? 'All Grades' : `Grade ${g}`}</option>)}
          </select>
          <select value={retailer} onChange={e => setRetailer(e.target.value)}>
            {RETAILER_OPTS.map(r => <option key={r}>{r === 'All' ? 'All Retailers' : r}</option>)}
          </select>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {filtered.length} results
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>GPU Name</th>
                <th>Retailer</th>
                <th>Old Price</th>
                <th>New Price</th>
                <th>Drop %</th>
                <th>Score</th>
                <th>Grade</th>
                <th>Date</th>
                <th>Link</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} cols={9} />)
              ) : filtered.length === 0 ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
                  {alerts.length === 0
                    ? 'No alerts yet — run a scrape to start tracking deals.'
                    : 'No alerts match your current filters.'}
                </td></tr>
              ) : (
                filtered.map(a => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 500, maxWidth: 200 }}>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>
                        {a.gpu_name}
                      </div>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                      {a.retailer}
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 13, color: 'var(--text-muted)', textDecoration: 'line-through' }}>
                        {formatPrice(a.old_price)}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>
                        {formatPrice(a.new_price)}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ color: 'var(--grade-a)', fontWeight: 700, fontSize: 13 }}>
                        -{a.drop_pct?.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 13, color: 'var(--accent)' }}>
                        {a.score?.toFixed(1)}
                      </span>
                    </td>
                    <td><GradeBadge grade={a.grade} pulse={a.grade === 'A'} /></td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {formatDate(a.created_at)}
                    </td>
                    <td>
                      {a.link && (
                        <a
                          href={a.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-block',
                            padding: '4px 10px',
                            background: 'var(--accent-dim)',
                            border: '1px solid rgba(245,166,35,0.3)',
                            color: 'var(--accent)',
                            borderRadius: 5,
                            fontSize: 11,
                            textDecoration: 'none',
                            fontWeight: 600,
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
