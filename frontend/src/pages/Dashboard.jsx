import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getPrices, triggerScrape } from '../api/prices'
import { getAlerts } from '../api/alerts'
import GradeBadge from '../components/GradeBadge'
import { SkeletonRow, SkeletonCard, Spinner } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { formatPrice, formatPercent, formatDate } from '../utils/formatters'

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="card" style={{ padding: '20px 22px', flex: 1 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10 }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 26, fontWeight: 600,
        color: accent || 'var(--text-primary)',
        marginBottom: 4,
      }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>}
    </div>
  )
}

const RETAILER_OPTS = ['All', 'newegg', 'walmart', 'amazon', 'ebay']

export default function Dashboard() {
  const [prices, setPrices] = useState([])
  const [alerts, setAlerts] = useState([])
  const [pricesLoading, setPricesLoading] = useState(true)
  const [alertsLoading, setAlertsLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [retailer, setRetailer] = useState('All')
  const [search, setSearch] = useState('')
  const toast = useToast()

  const loadPrices = useCallback(async () => {
    setPricesLoading(true)
    try {
      const params = {}
      if (retailer !== 'All') params.retailer = retailer
      if (search) params.query = search
      const { data } = await getPrices(params)
      setPrices(data)
    } catch {
      toast.error('Failed to load prices')
    } finally {
      setPricesLoading(false)
    }
  }, [retailer, search])

  const loadAlerts = useCallback(async () => {
    setAlertsLoading(true)
    try {
      const { data } = await getAlerts({ limit: 10 })
      setAlerts(data)
    } catch {
      toast.error('Failed to load alerts')
    } finally {
      setAlertsLoading(false)
    }
  }, [])

  useEffect(() => { loadPrices() }, [loadPrices])
  useEffect(() => { loadAlerts() }, [loadAlerts])

  const [countdown, setCountdown] = useState(null)

  const handleScrape = async () => {
    setScraping(true)
    try {
      await triggerScrape()
      let secs = 15
      setCountdown(secs)
      const interval = setInterval(() => {
        secs -= 1
        if (secs <= 0) {
          clearInterval(interval)
          setCountdown(null)
          setScraping(false)
          loadPrices()
          loadAlerts()
        } else {
          setCountdown(secs)
        }
      }, 1000)
    } catch {
      toast.error('Scrape failed. Check backend logs.')
      setScraping(false)
    }
  }

  // Stats
  const totalGPUs = prices.length
  const lowestToday = prices.length ? Math.min(...prices.map(p => p.price)) : null
  const lowestGPU = prices.find(p => p.price === lowestToday)
  const activeAlerts = alerts.length
  const lastScrape = prices.length ? prices[0]?.scraped_at : null

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            GPU deal tracker — live prices across Newegg, Walmart, Amazon, eBay
          </div>
        </div>
        <button
          onClick={handleScrape}
          disabled={scraping}
          style={{
            padding: '10px 18px',
            background: scraping ? 'var(--accent-dim)' : 'var(--accent)',
            color: scraping ? 'var(--accent)' : '#0D0F14',
            fontWeight: 600,
            border: '1px solid var(--accent)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 13,
          }}
        >
          {scraping ? <><Spinner size={13} /> Refreshing in {countdown}s…</> : '▶ Run Scrape Now'}
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 14, marginBottom: 28 }}>
        <StatCard
          label="GPUs Tracked"
          value={pricesLoading ? '—' : totalGPUs}
          sub="unique listings"
        />
        <StatCard
          label="Lowest Price Today"
          value={pricesLoading || !lowestToday ? '—' : formatPrice(lowestToday)}
          sub={lowestGPU?.name?.slice(0, 30) || ''}
          accent="var(--accent)"
        />
        <StatCard
          label="Active Alerts"
          value={alertsLoading ? '—' : activeAlerts}
          sub="price drop events"
          accent={activeAlerts > 0 ? 'var(--grade-a)' : undefined}
        />
        <StatCard
          label="Last Scraped"
          value={pricesLoading || !lastScrape ? '—' : formatDate(lastScrape).split(',')[0]}
          sub={lastScrape ? formatDate(lastScrape).split(',')[1]?.trim() : 'never'}
        />
      </div>

      {/* Two-column content */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Recent Alerts */}
        <div className="card">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>Recent Alerts</div>
            <Link to="/alerts" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>View all →</Link>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>GPU</th>
                  <th>Drop</th>
                  <th>Grade</th>
                  <th>Link</th>
                </tr>
              </thead>
              <tbody>
                {alertsLoading ? (
                  Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} cols={4} />)
                ) : alerts.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 28 }}>
                    No alerts yet — run a scrape to get started.
                  </td></tr>
                ) : (
                  alerts.slice(0, 8).map(a => (
                    <tr key={a.id}>
                      <td style={{ maxWidth: 160 }}>
                        <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {a.gpu_name}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.retailer}</div>
                      </td>
                      <td>
                        <span className="mono" style={{ color: 'var(--grade-a)', fontSize: 13, fontWeight: 600 }}>
                          -{a.drop_pct?.toFixed(1)}%
                        </span>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {formatPrice(a.new_price)}
                        </div>
                      </td>
                      <td><GradeBadge grade={a.grade} score={a.score} pulse={a.grade === 'A'} /></td>
                      <td>
                        {a.link && (
                          <a href={a.link} target="_blank" rel="noopener noreferrer"
                            style={{ color: 'var(--accent)', fontSize: 12, textDecoration: 'none' }}>
                            ↗
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

        {/* Current Prices */}
        <div className="card">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>Current Prices</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                placeholder="Search GPU…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ flex: 1 }}
              />
              <select value={retailer} onChange={e => setRetailer(e.target.value)}>
                {RETAILER_OPTS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <div style={{ overflowX: 'auto', maxHeight: 420, overflowY: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>GPU</th>
                  <th>Price</th>
                  <th>Retailer</th>
                  <th>Grade</th>
                </tr>
              </thead>
              <tbody>
                {pricesLoading ? (
                  Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} cols={4} />)
                ) : prices.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 28 }}>
                    No prices yet — run a scrape to get started.
                  </td></tr>
                ) : (
                  prices.map((p, i) => (
                    <tr key={`${p.name}-${p.retailer}-${i}`}>
                      <td style={{ maxWidth: 150 }}>
                        <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {p.name}
                        </div>
                      </td>
                      <td>
                        <span className="mono" style={{ fontWeight: 600, fontSize: 13 }}>
                          {formatPrice(p.price, p.currency)}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                        {p.retailer}
                      </td>
                      <td>
                        {p.grade ? <GradeBadge grade={p.grade} score={p.score} /> : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '10px 20px', borderTop: '1px solid var(--border)' }}>
            <Link to="/prices" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
              View full price browser →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
