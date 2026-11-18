import { useState, type FormEvent } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { Sparkles } from "lucide-react"

export default function Login() {
  const { user, login, register } = useAuth()
  const [mode, setMode] = useState<"login" | "register">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [fullName, setFullName] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/dashboard" replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(""); setLoading(true)
    try {
      if (mode === "login") await login(email, password)
      else await register(email, password, fullName || undefined)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === "string" ? detail : "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-600/20 mb-4">
            <Sparkles className="w-8 h-8 text-brand-500" />
          </div>
          <h1 className="text-3xl font-bold text-slate-100">DocIntel</h1>
          <p className="text-slate-500 mt-2">Intelligent Document Management</p>
        </div>
        <div className="bg-slate-900 rounded-2xl p-8 border border-slate-800 shadow-xl">
          <div className="flex mb-6 bg-slate-800 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition ${
                mode === "login" ? "bg-brand-600 text-white" : "text-slate-400"
              }`}
            >Sign in</button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition ${
                mode === "register" ? "bg-brand-600 text-white" : "text-slate-400"
              }`}
            >Register</button>
          </div>
          <form onSubmit={onSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-sm text-slate-400 mb-1">Full name</label>
                <input
                  type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
                  placeholder="Optional"
                />
              </div>
            )}
            <div>
              <label className="block text-sm text-slate-400 mb-1">Email</label>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Password</label>
              <input
                type="password" required minLength={8} value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            {error && (
              <div className="text-red-400 text-sm bg-red-950/50 border border-red-900 rounded-lg p-3">
                {error}
              </div>
            )}
            <button
              type="submit" disabled={loading}
              className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium transition"
            >
              {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
