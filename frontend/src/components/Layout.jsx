import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: '⬡' },
  { to: '/prices', label: 'Prices', icon: '◈' },
  { to: '/alerts', label: 'Alerts', icon: '◉' },
  { to: '/settings', label: 'Settings', icon: '◎' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-base)' }}>
      <aside style={{
        width: 210,
        flexShrink: 0,
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
      }}>
        {/* Logo — single line */}
        <div style={{ padding: '18px 16px 16px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 26, height: 26,
              background: 'var(--accent-dim)',
              border: '1px solid var(--accent)',
              borderRadius: 6,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, flexShrink: 0,
            }}>⬡</div>
            <span style={{
              fontSize: 14, fontWeight: 700,
              fontFamily: 'JetBrains Mono, monospace',
              color: 'var(--text-primary)',
              letterSpacing: '-0.01em',
            }}>GPU Tracker</span>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ padding: '10px 8px', flex: 1 }}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 9,
                padding: '8px 10px',
                borderRadius: 6,
                marginBottom: 2,
                textDecoration: 'none',
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-dim)' : 'transparent',
                border: isActive ? '1px solid rgba(245,166,35,0.2)' : '1px solid transparent',
                transition: 'all 0.15s',
              })}
            >
              <span style={{ fontSize: 13, opacity: 0.7 }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div style={{ padding: '12px 12px', borderTop: '1px solid var(--border)' }}>
          {user && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 7,
              marginBottom: 8,
            }}>
              <div style={{
                width: 22, height: 22, borderRadius: '50%',
                background: 'var(--accent-dim)',
                border: '1px solid var(--accent)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, color: 'var(--accent)', fontWeight: 700, flexShrink: 0,
              }}>
                {user.email?.[0]?.toUpperCase()}
              </div>
              <div style={{
                fontSize: 11, color: 'var(--text-muted)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                flex: 1,
              }}>
                {user.email}
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '7px 10px',
              background: 'transparent',
              border: '1px solid var(--border-light)',
              color: 'var(--text-muted)',
              borderRadius: 5,
              fontSize: 12,
              textAlign: 'left',
              display: 'flex', alignItems: 'center', gap: 7,
              cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 11 }}>↩</span> Sign out
          </button>
        </div>
      </aside>

      <main style={{ marginLeft: 210, flex: 1, minHeight: '100vh', padding: '24px 28px' }}>
        {children}
      </main>
    </div>
  )
}
