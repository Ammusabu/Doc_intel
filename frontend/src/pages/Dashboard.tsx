import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { FileText, CheckCircle2, Clock, MessageSquare, Upload, Search as SearchIcon, Sparkles } from "lucide-react"
import { api } from "../lib/api"
import type { DocumentListOut, Conversation } from "../lib/types"
import { useAuth } from "../context/AuthContext"
import StatCard from "../components/StatCard"
import { categoryChip, formatBytes, formatDate, STATUS_STYLES } from "../lib/categories"

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [docs, setDocs] = useState<DocumentListOut | null>(null)
  const [convs, setConvs] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get<DocumentListOut>("/documents?page=1&page_size=100"),
      api.get<Conversation[]>("/chat/conversations"),
    ])
      .then(([d, c]) => { setDocs(d.data); setConvs(c.data) })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false))
  }, [])

  const items = docs?.items ?? []
  const total = docs?.total ?? 0
  const completed = items.filter((d) => d.status === "completed").length
  const processing = items.filter((d) => d.status === "processing" || d.status === "pending").length

  const byCategory: Record<string, number> = {}
  for (const d of items) {
    if (d.predicted_category) {
      byCategory[d.predicted_category] = (byCategory[d.predicted_category] ?? 0) + 1
    }
  }
  const categoryRows = Object.entries(byCategory).sort((a, b) => b[1] - a[1])
  const maxCategory = Math.max(1, ...categoryRows.map(([, n]) => n))
  const recent = [...items].slice(0, 5)

  if (loading) {
    return <div className="p-8 text-slate-400">Loading dashboard...</div>
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-slate-400 mt-1">Welcome back, {user?.full_name ?? user?.email}</p>
        </div>
        <button
          onClick={() => navigate("/documents")}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition"
        >
          <Upload className="w-4 h-4" />
          Upload document
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total documents" value={total} icon={FileText} />
        <StatCard label="Completed" value={completed} icon={CheckCircle2} accent="text-emerald-500" />
        <StatCard label="Processing" value={processing} icon={Clock} accent="text-yellow-500" />
        <StatCard label="Conversations" value={convs.length} icon={MessageSquare} accent="text-violet-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Documents by category</h2>
          {categoryRows.length === 0 ? (
            <p className="text-slate-500 text-sm">No categorized documents yet.</p>
          ) : (
            <div className="space-y-3">
              {categoryRows.map(([cat, count]) => (
                <div key={cat}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-300">{cat}</span>
                    <span className="text-sm text-slate-400">{count}</span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-500 rounded-full"
                      style={{ width: `${(count / maxCategory) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Recent uploads</h2>
          {recent.length === 0 ? (
            <p className="text-slate-500 text-sm">No documents yet. Upload your first one to get started.</p>
          ) : (
            <div className="space-y-3">
              {recent.map((d) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-slate-200 truncate">{d.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {formatBytes(d.file_size_bytes)} · {formatDate(d.created_at)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-3">
                    {d.predicted_category && (
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${categoryChip(d.predicted_category)}`}>
                        {d.predicted_category}
                      </span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLES[d.status]}`}>
                      {d.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">Quick actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={() => navigate("/documents")}
            className="flex items-center gap-3 p-4 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 transition text-left"
          >
            <Upload className="w-5 h-5 text-brand-500" />
            <div>
              <div className="text-sm font-medium text-slate-100">Upload document</div>
              <div className="text-xs text-slate-500">PDF, DOCX, or TXT</div>
            </div>
          </button>
          <button
            onClick={() => navigate("/search")}
            className="flex items-center gap-3 p-4 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 transition text-left"
          >
            <SearchIcon className="w-5 h-5 text-brand-500" />
            <div>
              <div className="text-sm font-medium text-slate-100">Search documents</div>
              <div className="text-xs text-slate-500">Semantic + keyword hybrid</div>
            </div>
          </button>
          <button
            onClick={() => navigate("/chat")}
            className="flex items-center gap-3 p-4 rounded-lg bg-slate-800 hover:bg-slate-750 border border-slate-700 transition text-left"
          >
            <Sparkles className="w-5 h-5 text-brand-500" />
            <div>
              <div className="text-sm font-medium text-slate-100">Ask AI</div>
              <div className="text-xs text-slate-500">RAG with citations</div>
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}
