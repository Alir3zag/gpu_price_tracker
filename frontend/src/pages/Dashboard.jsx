import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getPrices, triggerScrape } from '../api/prices'
import { getAlerts } from '../api/alerts'
import GradeBadge from '../components/GradeBadge'
import { Spinner } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { formatPrice, formatDate, shortGPUName } from '../utils/formatters'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, accent }) {
  return (
    <div className="card" style={{ padding: '18px 20px', flex: 1 }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, fontWeight: 600, color: accent || 'var(--text-primary)', marginBottom: 3 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {sub}
        </div>
      )}
    </div>
  )
}

// ── Best deal card ────────────────────────────────────────────────────────────
function BestDealCard({ price }) {
  const dealLabel = price.score >= 80 ? 'Exceptional deal'
    : price.score >= 60 ? 'Good deal'
    : 'Fair deal'

  const scoreColor = price.score >= 80 ? 'var(--grade-a)'
    : price.score >= 60 ? 'var(--grade-b)'
    : 'var(--grade-c)'

  return (
    <div style={{ padding: '13px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12 }}>
      {/* Grade + score stacked */}
      <div style={{ textAlign: 'center', flexShrink: 0, width: 48 }}>
        <GradeBadge grade={price.grade} pulse={price.grade === 'A'} />
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: scoreColor, fontWeight: 700, marginTop: 4 }}>
          {Math.round(price.score)}/100
        </div>
      </div>

      {/* Name + meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }} title={price.name}>
          {shortGPUName(price.name)}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, fontWeight: 600, color: scoreColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {dealLabel}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>· {price.retailer}</span>
        </div>
      </div>

      {/* Price + buy */}
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
          {formatPrice(price.price, price.currency)}
        </div>
        {price.link && (
          <a href={price.link} target="_blank" rel="noopener noreferrer" style={{
            display: 'inline-block', marginTop: 4,
            padding: '3px 8px',
            background: 'var(--accent-dim)', border: '1px solid rgba(245,166,35,0.3)',
            color: 'var(--accent)', borderRadius: 4, fontSize: 10, fontWeight: 600, textDecoration: 'none',
          }}>
            Buy ↗
          </a>
        )}
      </div>
    </div>
  )
}

// ── Alert row ─────────────────────────────────────────────────────────────────
function AlertRow({ alert }) {
  return (
    <div style={{ padding: '11px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)', marginBottom: 2 }} title={alert.gpu_name}>
          {shortGPUName(alert.gpu_name)}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
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
        <a href={alert.link} target="_blank" rel="noopener noreferrer"
          style={{ color: 'var(--accent)', fontSize: 13, textDecoration: 'none', flexShrink: 0 }}>↗</a>
      )}
    </div>
  )
}

// ── Alerts summary (when few alerts exist) ────────────────────────────────────
function AlertsSummary({ alerts }) {
  const gradeCounts = { A: 0, B: 0, C: 0, D: 0 }
  alerts.forEach(a => { if (gradeCounts[a.grade] !== undefined) gradeCounts[a.grade]++ })

  const chartData = [
    { grade: 'A', count: gradeCounts.A, color: 'var(--grade-a)' },
    { grade: 'B', count: gradeCounts.B, color: 'var(--grade-b)' },
    { grade: 'C', count: gradeCounts.C, color: 'var(--grade-c)' },
    { grade: 'D', count: gradeCounts.D, color: 'var(--grade-d)' },
  ]

  const totalAlerts = alerts.length
  const avgDrop = totalAlerts
    ? (alerts.reduce((s, a) => s + (a.drop_pct || 0), 0) / totalAlerts).toFixed(1)
    : 0
  const bestScore = totalAlerts
    ? Math.round(Math.max(...alerts.map(a => a.score || 0)))
    : 0

  return (
    <div style={{ padding: '16px' }}>
      {/* Mini stats */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16 }}>
        {[
          { label: 'Total', value: totalAlerts },
          { label: 'Avg Drop', value: `${avgDrop}%` },
          { label: 'Best Score', value: bestScore },
        ].map(({ label, value }) => (
          <div key={label} style={{ flex: 1, textAlign: 'center', padding: '10px 8px', background: 'var(--bg-base)', borderRadius: 6, margin: '0 3px' }}>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, fontWeight: 700, color: 'var(--accent)' }}>{value}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Bar chart — alerts by grade */}
      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
        Alerts by Grade
      </div>
      <ResponsiveContainer width="100%" height={90}>
        <BarChart data={chartData} margin={{ top: 0, right: 4, bottom: 0, left: -20 }}>
          <XAxis dataKey="grade" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              return (
                <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-light)', borderRadius: 6, padding: '6px 10px', fontSize: 12 }}>
                  Grade {payload[0].payload.grade}: <strong>{payload[0].value}</strong> alert{payload[0].value !== 1 ? 's' : ''}
                </div>
              )
            }}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
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
      const { data } = await getAlerts({ limit: 20 })
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

  const totalGPUs = prices.length
  const lowestToday = prices.length ? Math.min(...prices.map(p => p.price)) : null
  const lowestGPU = prices.find(p => p.price === lowestToday)
  const lastScrape = prices.length ? prices[0]?.scraped_at : null
  const bestDeals = prices.filter(p => p.score && p.score >= 40).slice(0, 5)
  const recentAlerts = alerts
    .filter((a, i, arr) => arr.findIndex(x => x.gpu_name === a.gpu_name) === i)
    .slice(0, 5)

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 22 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Dashboard</h1>
        <button
          onClick={handleScrape}
          disabled={scraping}
          style={{
            padding: '9px 16px',
            background: scraping ? 'var(--accent-dim)' : 'var(--accent)',
            color: scraping ? 'var(--accent)' : '#0D0F14',
            fontWeight: 600, border: '1px solid var(--accent)',
            borderRadius: 7, display: 'flex', alignItems: 'center', gap: 7,
            fontSize: 13, cursor: scraping ? 'default' : 'pointer',
          }}
        >
          {scraping ? <><Spinner size={12} /> Refreshing in {countdown}s…</> : '▶ Run Scrape'}
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <StatCard label="GPUs Tracked" value={pricesLoading ? '—' : totalGPUs} sub="unique listings" />
        <StatCard
          label="Cheapest Listing"
          value={pricesLoading || !lowestToday ? '—' : formatPrice(lowestToday)}
          sub={lowestGPU ? shortGPUName(lowestGPU.name) : ''}
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

      {/* Two columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Left: Best Deals */}
        <div className="card">
          <div style={{ padding: '13px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>🔥 Best Deals Right Now</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Highest-scored listings · score = 0–100</div>
            </div>
            <div style={{ display: 'flex', gap: 8, fontSize: 10 }}>
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
              No scored deals yet — run a scrape to find opportunities.
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

        {/* Right: Recent drops + chart */}
        <div className="card">
          <div style={{ padding: '13px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>Recent Price Drops</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Prices that fell since last scrape</div>
            </div>
            <Link to="/alerts" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>View all →</Link>
          </div>

          {alertsLoading ? (
            <div style={{ padding: 20 }}>
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div className="skeleton" style={{ height: 13, width: '65%', marginBottom: 6 }} />
                  <div className="skeleton" style={{ height: 10, width: '35%' }} />
                </div>
              ))}
            </div>
          ) : alerts.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No price drops detected yet.<br />
              <span style={{ fontSize: 11, marginTop: 6, display: 'block' }}>
                Run a second scrape to compare prices.
              </span>
            </div>
          ) : (
            <>
              {recentAlerts.map(a => <AlertRow key={a.id} alert={a} />)}
              {/* Summary + chart when we have data */}
              <AlertsSummary alerts={alerts} />
            </>
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