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
      {/* Sidebar */}
      <aside style={{
        width: 220,
        flexShrink: 0,
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        top: 0, left: 0, bottom: 0,
      }}>
        {/* Logo */}
        <div style={{ padding: '24px 20px 20px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32, height: 32,
              background: 'var(--accent-dim)',
              border: '1px solid var(--accent)',
              borderRadius: 7,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14,
            }}>⬡</div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>GPU</div>
              <div style={{ fontSize: 10, color: 'var(--accent)', letterSpacing: '0.12em', fontWeight: 600 }}>TRACKER</div>
            </div>
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ padding: '12px 10px', flex: 1 }}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 7,
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
              <span style={{ fontSize: 14, opacity: 0.8 }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User + logout */}
        <div style={{ padding: '16px 14px', borderTop: '1px solid var(--border)' }}>
          {user && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10, wordBreak: 'break-all' }}>
              {user.email}
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '8px 12px',
              background: 'transparent',
              border: '1px solid var(--border-light)',
              color: 'var(--text-secondary)',
              borderRadius: 6,
              fontSize: 12,
              textAlign: 'left',
              display: 'flex', alignItems: 'center', gap: 8,
            }}
          >
            <span>↩</span> Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ marginLeft: 220, flex: 1, minHeight: '100vh', padding: '28px 32px' }}>
        {children}
      </main>
    </div>
  )
}
