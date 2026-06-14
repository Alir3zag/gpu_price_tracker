import { useState, useEffect, useCallback } from 'react'
import { getPrices, getPriceHistory } from '../api/prices'
import GradeBadge from '../components/GradeBadge'
import { SkeletonRow, Spinner } from '../components/Skeleton'
import { useToast } from '../components/Toast'
import { formatPrice, formatDate, formatDateShort, shortGPUName } from '../utils/formatters'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts'

const RETAILER_OPTS = ['All', 'newegg', 'walmart', 'amazon', 'ebay']
const RETAILER_COLORS = {
  newegg: '#F5A623', walmart: '#3B82F6', amazon: '#22C55E', ebay: '#A855F7',
}
const PAGE_SIZE = 20



function PriceHistoryModal({ gpu, onClose }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const toast = useToast()

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await getPriceHistory(gpu)
        setHistory(data)
      } catch {
        toast.error('Failed to load price history')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [gpu])

  const retailers = [...new Set(history.map(h => h.retailer))]
  const dateMap = {}
  history.forEach(h => {
    const d = formatDateShort(h.scraped_at)
    if (!dateMap[d]) dateMap[d] = { date: d }
    dateMap[d][h.retailer] = h.price
  })
  const chartData = Object.values(dateMap)

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border-light)',
        borderRadius: 7, padding: '10px 14px',
      }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
        {payload.map(p => (
          <div key={p.dataKey} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, marginBottom: 2 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: p.color }} />
            <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{p.dataKey}:</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{formatPrice(p.value)}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 100, backdropFilter: 'blur(4px)',
      }}
    >
      <div
        className="card"
        onClick={e => e.stopPropagation()}
        style={{ width: '90%', maxWidth: 740, padding: 26 }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 18 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 3 }} title={gpu}>
              {shortGPUName(gpu)}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Price history across all retailers</div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', color: 'var(--text-muted)', fontSize: 18, padding: '2px 6px', cursor: 'pointer' }}
          >✕</button>
        </div>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, gap: 10, color: 'var(--text-muted)' }}>
            <Spinner size={18} /> Loading history…
          </div>
        ) : history.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40, fontSize: 13 }}>
            No history data yet for this GPU.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
                tickFormatter={v => `$${v}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend formatter={v => (
                <span style={{ fontSize: 12, textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{v}</span>
              )} />
              {retailers.map(r => (
                <Line
                  key={r} type="monotone" dataKey={r}
                  stroke={RETAILER_COLORS[r] || '#8892A4'}
                  strokeWidth={2}
                  dot={{ r: 3, fill: RETAILER_COLORS[r] || '#8892A4' }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

export default function Prices() {
  const [prices, setPrices] = useState([])
  const [loading, setLoading] = useState(true)
  const [retailer, setRetailer] = useState('All')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('price')
  const [page, setPage] = useState(0)
  const [selectedGPU, setSelectedGPU] = useState(null)
  const toast = useToast()

  const loadPrices = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: 200 }
      if (retailer !== 'All') params.retailer = retailer
      if (search) params.query = search
      const { data } = await getPrices(params)
      const sorted = [...data].sort((a, b) => {
        if (sortBy === 'price') return a.price - b.price
        if (sortBy === 'name') return a.name.localeCompare(b.name)
        if (sortBy === 'retailer') return a.retailer.localeCompare(b.retailer)
        return 0
      })
      setPrices(sorted)
      setPage(0)
    } catch {
      toast.error('Failed to load prices')
    } finally {
      setLoading(false)
    }
  }, [retailer, search, sortBy])

  useEffect(() => { loadPrices() }, [loadPrices])

  const paged = prices.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(prices.length / PAGE_SIZE)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Prices</h1>
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          Click any row to see price history
        </div>
      </div>

      <div className="card">
        {/* Filters */}
        <div style={{
          padding: '14px 16px', borderBottom: '1px solid var(--border)',
          display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center',
        }}>
          <input
            placeholder="Search GPU…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ flex: '1 1 140px', minWidth: 0 }}
          />
          <select value={retailer} onChange={e => setRetailer(e.target.value)}>
            {RETAILER_OPTS.map(r => <option key={r}>{r === 'All' ? 'All retailers' : r}</option>)}
          </select>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="price">Price ↑</option>
            <option value="name">Name A–Z</option>
            <option value="retailer">Retailer</option>
          </select>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
            {prices.length} results
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: '45%' }}>GPU</th>
                <th>Price</th>
                <th>Grade</th>
                <th>Retailer</th>
                <th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} cols={5} />)
              ) : paged.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 36, fontSize: 13 }}>
                    No prices found. Adjust filters or run a scrape.
                  </td>
                </tr>
              ) : (
                paged.map((p, i) => (
                  <tr
                    key={i}
                    onClick={() => setSelectedGPU(p.name)}
                    style={{ cursor: 'pointer' }}
                    title={p.name}
                  >
                    <td>
                      <div style={{
                        fontWeight: 500, fontSize: 12,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        maxWidth: 320,
                      }}>
                        {shortGPUName(p.name)}
                      </div>
                    </td>
                    <td>
                      <span className="mono" style={{ fontWeight: 700, fontSize: 13 }}>
                        {formatPrice(p.price, p.currency)}
                      </span>
                    </td>
                    <td>
                      {p.grade
                        ? <GradeBadge grade={p.grade} score={p.score} />
                        : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                      {p.retailer}
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {formatDate(p.scraped_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div style={{
            padding: '12px 16px', borderTop: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              style={{ padding: '5px 12px', background: 'var(--bg-base)', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', cursor: 'pointer' }}
            >← Prev</button>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              style={{ padding: '5px 12px', background: 'var(--bg-base)', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', cursor: 'pointer' }}
            >Next →</button>
          </div>
        )}
      </div>

      {selectedGPU && (
        <PriceHistoryModal gpu={selectedGPU} onClose={() => setSelectedGPU(null)} />
      )}
    </div>
  )
}
