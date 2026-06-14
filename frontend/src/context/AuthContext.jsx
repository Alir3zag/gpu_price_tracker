import { createContext, useContext, useState, useEffect } from 'react'
import { login as apiLogin, getMe } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      const stored = localStorage.getItem('token')
      if (stored) {
        try {
          const { data } = await getMe()
          setUser(data)
          setToken(stored)
        } catch {
          localStorage.removeItem('token')
          setToken(null)
        }
      }
      setLoading(false)
    }
    init()
  }, [])

  const login = async (email, password) => {
    const { data } = await apiLogin(email, password)
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
    const me = await getMe()
    setUser(me.data)
    return me.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
