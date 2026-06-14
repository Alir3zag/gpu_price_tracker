import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getPrices, triggerScrape } from '../api/prices'
import { getAlerts } from '../api/alerts'
import GradeBadge from '../components/GradeBadge'
import { Spinner } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { formatPrice, formatDate } from '../utils/formatters'

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="card" style={{ padding: '18px 20px', flex: 1 }}>
      <div style={{
        fontSize: 10, color: 'var(--text-muted)', fontWeight: 600,
        letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 24, fontWeight: 600,
        color: accent || 'var(--text-primary)',
        marginBottom: 3,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{
          fontSize: 11, color: 'var(--text-muted)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{sub}</div>
      )}
    </div>
  )
}

function shortName(name) {
  if (!name) return '—'
  return name
    .replace(/PCI Express \d+\.\d+/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 52)
}

// Best deal card — shows top scored current prices
function BestDealCard({ price }) {
  const dropLabel = price.score >= 80 ? 'Exceptional deal'
    : price.score >= 60 ? 'Good deal'
    : price.score >= 40 ? 'Fair deal'
    : 'Below average'

  return (
    <div style={{
      padding: '14px 16px',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', gap: 14,
    }}>
      <GradeBadge grade={price.grade} pulse={price.grade === 'A'} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 12, fontWeight: 600,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          color: 'var(--text-primary)', marginBottom: 3,
        }} title={price.name}>
          {shortName(price.name)}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontSize: 10, fontWeight: 600,
            color: price.grade === 'A' ? 'var(--grade-a)'
              : price.grade === 'B' ? 'var(--grade-b)'
              : 'var(--text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>
            {dropLabel}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>·</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
            {price.retailer}
          </span>
        </div>
      </div>

      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 15, fontWeight: 700,
          color: 'var(--text-primary)',
        }}>
          {formatPrice(price.price, price.currency)}
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
          Score {Math.round(price.score)}
        </div>
      </div>

      {price.link && (
        <a
          href={price.link}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            padding: '5px 10px',
            background: 'var(--accent-dim)',
            border: '1px solid rgba(245,166,35,0.3)',
            color: 'var(--accent)',
            borderRadius: 5,
            fontSize: 11, fontWeight: 600,
            textDecoration: 'none', flexShrink: 0,
          }}
        >
          Buy ↗
        </a>
      )}
    </div>
  )
}

// Recent alert row — what changed since last scrape
function AlertRow({ alert }) {
  return (
    <div style={{
      padding: '12px 16px',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 12, fontWeight: 500,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          color: 'var(--text-primary)',
        }} title={alert.gpu_name}>
          {shortName(alert.gpu_name)}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, textTransform: 'capitalize' }}>
          {alert.retailer} · {formatDate(alert.created_at)}
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <span className="mono" style={{ color: 'var(--grade-a)', fontWeight: 700, fontSize: 13 }}>
          -{alert.drop_pct?.toFixed(1)}%
        </span>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {formatPrice(alert.old_price)} → {formatPrice(alert.new_price)}
        </div>
      </div>
      <GradeBadge grade={alert.grade} />
      {alert.link && (
        <a
          href={alert.link}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--accent)', fontSize: 13, textDecoration: 'none', flexShrink: 0 }}
        >↗</a>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [prices, setPrices] = useState([])
  const [alerts, setAlerts] = useState([])
  const [pricesLoading, setPricesLoading] = useState(true)
  const [alertsLoading, setAlertsLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [countdown, setCountdown] = useState(null)
  const toast = useToast()

  const loadPrices = useCallback(async () => {
    setPricesLoading(true)
    try {
      const { data } = await getPrices({ limit: 50 })
      setPrices(data)
    } catch {
      toast.error('Failed to load prices')
    } finally {
      setPricesLoading(false)
    }
  }, [])

  const loadAlerts = useCallback(async () => {
    setAlertsLoading(true)
    try {
      const { data } = await getAlerts({ limit: 6 })
      setAlerts(data)
    } catch {
      toast.error('Failed to load alerts')
    } finally {
      setAlertsLoading(false)
    }
  }, [])

  useEffect(() => { loadPrices() }, [loadPrices])
  useEffect(() => { loadAlerts() }, [loadAlerts])

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
  const lastScrape = prices.length ? prices[0]?.scraped_at : null

  // Best deals = top 5 prices by score (already sorted by backend)
  const bestDeals = prices.filter(p => p.score && p.score >= 40).slice(0, 5)

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Dashboard</h1>
        <button
          onClick={handleScrape}
          disabled={scraping}
          style={{
            padding: '9px 16px',
            background: scraping ? 'var(--accent-dim)' : 'var(--accent)',
            color: scraping ? 'var(--accent)' : '#0D0F14',
            fontWeight: 600,
            border: '1px solid var(--accent)',
            borderRadius: 7,
            display: 'flex', alignItems: 'center', gap: 7,
            fontSize: 13,
            cursor: scraping ? 'default' : 'pointer',
          }}
        >
          {scraping
            ? <><Spinner size={12} /> Refreshing in {countdown}s…</>
            : '▶ Run Scrape'}
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <StatCard
          label="GPUs Tracked"
          value={pricesLoading ? '—' : totalGPUs}
          sub="unique listings"
        />
        <StatCard
          label="Best Price Today"
          value={pricesLoading || !lowestToday ? '—' : formatPrice(lowestToday)}
          sub={lowestGPU ? shortName(lowestGPU.name) : ''}
          accent="var(--accent)"
        />
        <StatCard
          label="Price Drops"
          value={alertsLoading ? '—' : alerts.length}
          sub="detected this session"
          accent={alerts.length > 0 ? 'var(--grade-a)' : undefined}
        />
        <StatCard
          label="Last Scraped"
          value={pricesLoading || !lastScrape ? '—' : formatDate(lastScrape).split(',')[0]}
          sub={lastScrape ? formatDate(lastScrape).split(',')[1]?.trim() : 'never'}
        />
      </div>

      {/* Two column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Left: Best Deals Right Now */}
        <div className="card">
          <div style={{
            padding: '13px 16px',
            borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>🔥 Best Deals Right Now</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                Highest-scored listings across all retailers
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, fontSize: 10, color: 'var(--text-muted)' }}>
              <span style={{ color: 'var(--grade-a)' }}>A 80+</span>
              <span style={{ color: 'var(--grade-b)' }}>B 60+</span>
              <span style={{ color: 'var(--grade-c)' }}>C 40+</span>
            </div>
          </div>

          {pricesLoading ? (
            <div style={{ padding: 20 }}>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div className="skeleton" style={{ height: 13, width: '65%', marginBottom: 6 }} />
                  <div className="skeleton" style={{ height: 10, width: '35%' }} />
                </div>
              ))}
            </div>
          ) : bestDeals.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No deals scored yet — run a scrape to find opportunities.
            </div>
          ) : (
            bestDeals.map((p, i) => <BestDealCard key={i} price={p} />)
          )}

          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--border)' }}>
            <Link to="/prices" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
              Browse all {totalGPUs > 0 ? `${totalGPUs} ` : ''}listings →
            </Link>
          </div>
        </div>

        {/* Right: Recent Price Drops */}
        <div className="card">
          <div style={{
            padding: '13px 16px',
            borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>Recent Price Drops</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                Prices that fell since last scrape
              </div>
            </div>
            <Link to="/alerts" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
              View all →
            </Link>
          </div>

          {alertsLoading ? (
            <div style={{ padding: 20 }}>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div className="skeleton" style={{ height: 13, width: '65%', marginBottom: 6 }} />
                  <div className="skeleton" style={{ height: 10, width: '35%' }} />
                </div>
              ))}
            </div>
          ) : alerts.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No price drops detected yet. Run a second scrape to compare prices.
            </div>
          ) : (
            alerts.map(a => <AlertRow key={a.id} alert={a} />)
          )}

          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--border)' }}>
            <Link to="/alerts" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
              Full alert history →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
