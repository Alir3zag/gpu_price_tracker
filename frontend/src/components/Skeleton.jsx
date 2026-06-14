export function SkeletonRow({ cols = 5 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i}>
          <div className="skeleton" style={{ height: 14, width: `${60 + Math.random() * 30}%` }} />
        </td>
      ))}
    </tr>
  )
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="skeleton" style={{ height: 12, width: '40%', marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 28, width: '60%', marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 10, width: '30%' }} />
    </div>
  )
}

export function Spinner({ size = 16 }) {
  return (
    <div style={{
      width: size, height: size,
      border: `2px solid var(--border-light)`,
      borderTop: `2px solid var(--accent)`,
      borderRadius: '50%',
      animation: 'spin 0.7s linear infinite',
      display: 'inline-block',
    }} />
  )
}

// Inject spin keyframe once
if (typeof document !== 'undefined' && !document.getElementById('spinner-style')) {
  const style = document.createElement('style')
  style.id = 'spinner-style'
  style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }'
  document.head.appendChild(style)
}
