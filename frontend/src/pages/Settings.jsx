import { useState, useEffect } from 'react'
import { getSettings, updateSettings } from '../api/settings'
import { useToast } from '../components/Toast'
import { Spinner } from '../components/Skeleton'

export default function Settings() {
  const [form, setForm] = useState({
    alert_threshold: 5.0,
    check_interval_hours: 6.0,
    search_queries: ['3090', '3080', '4090'],
    email_enabled: false,
    email_address: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newQuery, setNewQuery] = useState('')
  const toast = useToast()

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await getSettings()
        setForm({
          alert_threshold: data.alert_threshold ?? 5.0,
          check_interval_hours: data.check_interval_hours ?? 6.0,
          search_queries: data.search_queries ?? ['3090', '3080', '4090'],
          email_enabled: data.email_enabled ?? false,
          email_address: data.email_address ?? '',
        })
      } catch {
        toast.error('Failed to load settings')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateSettings(form)
      toast.success('Settings saved')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const addQuery = () => {
    const q = newQuery.trim()
    if (!q || form.search_queries.includes(q)) return
    setForm(f => ({ ...f, search_queries: [...f.search_queries, q] }))
    setNewQuery('')
  }

  const removeQuery = (q) =>
    setForm(f => ({ ...f, search_queries: f.search_queries.filter(x => x !== q) }))

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 40, color: 'var(--text-muted)' }}>
      <Spinner size={16} /> Loading settings…
    </div>
  )

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Settings</h1>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Configure your tracker preferences — changes apply to the next scheduled scrape
        </div>
      </div>

      <div style={{ maxWidth: 560 }}>

        {/* Scraping config */}
        <div className="card" style={{ padding: 24, marginBottom: 16 }}>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 18, color: 'var(--text-primary)' }}>
            Scraping Config
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, fontWeight: 500 }}>
              Alert threshold (%)
            </label>
            <input
              type="number"
              min={1}
              max={99}
              step={0.5}
              value={form.alert_threshold}
              onChange={e => setForm(f => ({ ...f, alert_threshold: parseFloat(e.target.value) }))}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
              Minimum price drop % to trigger an alert. Default: 5.0
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, fontWeight: 500 }}>
              Check interval (hours)
            </label>
            <input
              type="number"
              min={1}
              max={168}
              step={0.5}
              value={form.check_interval_hours}
              onChange={e => setForm(f => ({ ...f, check_interval_hours: parseFloat(e.target.value) }))}
              style={{ width: '100%' }}
            />
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
              How often to auto-scrape. Default: 6 hours
            </div>
          </div>
        </div>

        {/* Search queries */}
        <div className="card" style={{ padding: 24, marginBottom: 16 }}>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4, color: 'var(--text-primary)' }}>
            GPU Models to Track
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
            Search terms sent to each retailer. Broader = more results, slower scrapes.
          </div>

          {/* Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
            {form.search_queries.map(q => (
              <div key={q} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'var(--accent-dim)', border: '1px solid rgba(245,166,35,0.3)',
                borderRadius: 20, padding: '5px 12px',
                fontSize: 12, fontWeight: 500, fontFamily: 'JetBrains Mono, monospace',
                color: 'var(--accent)',
              }}>
                {q}
                <button
                  onClick={() => removeQuery(q)}
                  style={{ background: 'none', color: 'var(--accent)', fontSize: 14, opacity: 0.6, padding: 0, lineHeight: 1 }}
                >×</button>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <input
              placeholder="e.g. 4080, RX 7900"
              value={newQuery}
              onChange={e => setNewQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addQuery()}
              style={{ flex: 1 }}
            />
            <button
              onClick={addQuery}
              style={{
                padding: '8px 16px',
                background: 'var(--accent-dim)',
                border: '1px solid rgba(245,166,35,0.3)',
                color: 'var(--accent)',
                fontWeight: 600,
                fontSize: 13,
              }}
            >
              Add
            </button>
          </div>
        </div>

        {/* Email alerts */}
        <div className="card" style={{ padding: 24, marginBottom: 24 }}>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 18, color: 'var(--text-primary)' }}>
            Email Alerts
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', marginBottom: 16 }}>
            <div
              onClick={() => setForm(f => ({ ...f, email_enabled: !f.email_enabled }))}
              style={{
                width: 40, height: 22,
                background: form.email_enabled ? 'var(--accent)' : 'var(--border-light)',
                borderRadius: 11,
                position: 'relative',
                transition: 'background 0.2s',
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              <div style={{
                position: 'absolute',
                top: 3, left: form.email_enabled ? 21 : 3,
                width: 16, height: 16,
                background: form.email_enabled ? '#0D0F14' : 'var(--text-muted)',
                borderRadius: '50%',
                transition: 'left 0.2s',
              }} />
            </div>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Send email on price drop alerts
            </span>
          </label>

          {form.email_enabled && (
            <div>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6, fontWeight: 500 }}>
                Email address
              </label>
              <input
                type="email"
                value={form.email_address}
                onChange={e => setForm(f => ({ ...f, email_address: e.target.value }))}
                placeholder="you@example.com"
                style={{ width: '100%' }}
              />
            </div>
          )}
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: '12px 28px',
            background: saving ? 'var(--accent-dim)' : 'var(--accent)',
            color: saving ? 'var(--accent)' : '#0D0F14',
            fontWeight: 700,
            fontSize: 14,
            border: '1px solid var(--accent)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', gap: 8,
          }}
        >
          {saving ? <><Spinner size={13} /> Saving…</> : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
