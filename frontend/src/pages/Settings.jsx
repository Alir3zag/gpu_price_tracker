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
      toast.error(err.response?.data?.detail || 'Failed to save')
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

  const removeQuery = q =>
    setForm(f => ({ ...f, search_queries: f.search_queries.filter(x => x !== q) }))

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 40, color: 'var(--text-muted)' }}>
      <Spinner size={16} /> Loading…
    </div>
  )

  const Field = ({ label, hint, children }) => (
    <div style={{ marginBottom: 20 }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
        {label}
      </label>
      {children}
      {hint && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>{hint}</div>}
    </div>
  )

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>Settings</h1>

      <div style={{ maxWidth: 520, margin: '0 auto' }}>

        {/* Scraping */}
        <div className="card" style={{ padding: '20px 22px', marginBottom: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 18 }}>
            Scraping
          </div>

          <Field label="Alert threshold (%)" hint="Minimum price drop to trigger an alert. Default: 5%">
            <input
              type="number" min={1} max={99} step={0.5}
              value={form.alert_threshold}
              onChange={e => setForm(f => ({ ...f, alert_threshold: parseFloat(e.target.value) }))}
              style={{ width: '100%' }}
            />
          </Field>

          <Field label="Check interval (hours)" hint="How often to auto-scrape. Default: 6 hours">
            <input
              type="number" min={1} max={168} step={0.5}
              value={form.check_interval_hours}
              onChange={e => setForm(f => ({ ...f, check_interval_hours: parseFloat(e.target.value) }))}
              style={{ width: '100%' }}
            />
          </Field>
        </div>

        {/* GPU Models */}
        <div className="card" style={{ padding: '20px 22px', marginBottom: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>
            GPU Models to Track
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
            Search terms sent to each retailer.
          </div>

          {/* Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
            {form.search_queries.map(q => (
              <div key={q} style={{
                display: 'inline-flex', alignItems: 'center', gap: 5,
                padding: '5px 10px',
                background: 'var(--accent-dim)',
                border: '1px solid rgba(245,166,35,0.35)',
                borderRadius: 20,
                fontSize: 12, fontWeight: 600,
                fontFamily: 'JetBrains Mono, monospace',
                color: 'var(--accent)',
              }}>
                {q}
                <button
                  onClick={() => removeQuery(q)}
                  style={{ background: 'none', color: 'var(--accent)', fontSize: 14, padding: 0, lineHeight: 1, opacity: 0.6, cursor: 'pointer' }}
                >×</button>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 7 }}>
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
                padding: '8px 14px',
                background: 'var(--accent-dim)',
                border: '1px solid rgba(245,166,35,0.3)',
                color: 'var(--accent)',
                fontWeight: 600, fontSize: 13,
                borderRadius: 6, cursor: 'pointer',
              }}
            >Add</button>
          </div>
        </div>

        {/* Email */}
        <div className="card" style={{ padding: '20px 22px', marginBottom: 22 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 16 }}>
            Email Alerts
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', marginBottom: form.email_enabled ? 16 : 0 }}>
            <div
              onClick={() => setForm(f => ({ ...f, email_enabled: !f.email_enabled }))}
              style={{
                width: 38, height: 20,
                background: form.email_enabled ? 'var(--accent)' : 'var(--border-light)',
                borderRadius: 10, position: 'relative',
                transition: 'background 0.2s', cursor: 'pointer', flexShrink: 0,
              }}
            >
              <div style={{
                position: 'absolute', top: 2,
                left: form.email_enabled ? 20 : 2,
                width: 16, height: 16,
                background: form.email_enabled ? '#0D0F14' : 'var(--text-muted)',
                borderRadius: '50%', transition: 'left 0.2s',
              }} />
            </div>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Send email on price drops
            </span>
          </label>

          <div style={{ display: form.email_enabled ? 'block' : 'none' }}>
            <Field label="Email address">
              <input
                type="email"
                value={form.email_address}
                onChange={e => setForm(f => ({ ...f, email_address: e.target.value }))}
                placeholder="you@example.com"
                style={{ width: '100%' }}
              />
            </Field>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            width: '100%',
            padding: '12px 0',
            background: saving ? 'var(--accent-dim)' : 'var(--accent)',
            color: saving ? 'var(--accent)' : '#0D0F14',
            fontWeight: 700, fontSize: 14,
            border: '1px solid var(--accent)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            cursor: saving ? 'default' : 'pointer',
          }}
        >
          {saving ? <><Spinner size={13} /> Saving…</> : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
