import { useState, useEffect, createContext, useContext, useCallback } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'success') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3500)
  }, [])

  const toast = {
    success: (msg) => addToast(msg, 'success'),
    error: (msg) => addToast(msg, 'error'),
    info: (msg) => addToast(msg, 'info'),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        zIndex: 9999,
      }}>
        {toasts.map(t => (
          <div
            key={t.id}
            style={{
              background: t.type === 'success' ? 'rgba(34,197,94,0.12)' :
                          t.type === 'error' ? 'rgba(239,68,68,0.12)' : 'rgba(245,166,35,0.12)',
              border: `1px solid ${t.type === 'success' ? 'var(--grade-a)' :
                                    t.type === 'error' ? 'var(--grade-d)' : 'var(--accent)'}`,
              color: t.type === 'success' ? 'var(--grade-a)' :
                     t.type === 'error' ? 'var(--grade-d)' : 'var(--accent)',
              padding: '10px 16px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              minWidth: 220,
              backdropFilter: 'blur(8px)',
              animation: 'slideIn 0.2s ease-out',
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(20px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
