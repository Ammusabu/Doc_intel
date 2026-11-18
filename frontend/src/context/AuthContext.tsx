import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { api, TOKEN_KEY, type User } from "../lib/api"

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) { setLoading(false); return }
    api.get<User>("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string; user: User }>(
      "/auth/login", { email, password }
    )
    localStorage.setItem(TOKEN_KEY, res.data.access_token)
    setUser(res.data.user)
  }

  async function register(email: string, password: string, fullName?: string) {
    await api.post("/auth/register", { email, password, full_name: fullName })
    await login(email, password)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    window.location.href = "/login"
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider")
  return ctx
}
