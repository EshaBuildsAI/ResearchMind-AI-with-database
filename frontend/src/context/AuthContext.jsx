import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi } from '../api'
import { setTokens, clearTokens } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('rm_access_token')
    if (!token) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then(({ data }) => setUser(data))
      .catch(() => clearTokens())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (identifier, password) => {
    const { data } = await authApi.login({ identifier, password })
    if (data.requires_2fa) {
      return { requiresTwoFactor: true, pendingToken: data.pending_token }
    }
    setTokens(data)
    setUser(data.user)
    return { requiresTwoFactor: false, user: data.user }
  }, [])

  const completeLogin2fa = useCallback(async (pendingToken, code) => {
    const { data } = await authApi.login2fa(pendingToken, code)
    setTokens(data)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (username, email, password) => {
    await authApi.register({ username, email, password })
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // stateless JWT — even if the call fails, clear local tokens anyway
    }
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, completeLogin2fa, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
