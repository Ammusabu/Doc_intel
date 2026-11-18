import { useEffect, useState } from "react"
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, LineChart, Line,
} from "recharts"
import { FileText, TrendingUp, Search, MessageSquare } from "lucide-react"
import { api } from "../lib/api"
import type { DocumentListOut, Conversation } from "../lib/types"
import StatCard from "../components/StatCard"

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4", "#64748b"]

export default function Analytics() {
  const [docs, setDocs] = useState<DocumentListOut | null>(null)
  const [convs, setConvs] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get<DocumentListOut>("/documents?page=1&page_size=100"),
      api.get<Conversation[]>("/chat/conversations"),
    ])
      .then(([d, c]) => { setDocs(d.data); setConvs(c.data) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="p-8 text-slate-400">Loading analytics...</div>
  }

  const items = docs?.items ?? []

  const categoryData: { name: string; value: number }[] = []
  const catMap: Record<string, number> = {}
  for (const d of items) {
    if (d.predicted_category) {
      catMap[d.predicted_category] = (catMap[d.predicted_category] ?? 0) + 1
    }
  }
  for (const [k, v] of Object.entries(catMap)) categoryData.push({ name: k, value: v })

  const statusData = [
    { name: "Completed", value: items.filter((d) => d.status === "completed").length },
    { name: "Processing", value: items.filter((d) => d.status === "processing" || d.status === "pending").length },
    { name: "Failed", value: items.filter((d) => d.status === "failed").length },
  ].filter((s) => s.value > 0)

  const uploadsByDay: Record<string, number> = {}
  for (const d of items) {
    const day = new Date(d.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
    uploadsByDay[day] = (uploadsByDay[day] ?? 0) + 1
  }
  const uploadTrend = Object.entries(uploadsByDay)
    .map(([date, count]) => ({ date, uploads: count }))
    .sort((a, b) => new Date(a.date + " 2026").getTime() - new Date(b.date + " 2026").getTime())

  const avgConfidence = (() => {
    const withConf = items.filter((d) => d.classification_confidence != null)
    if (!withConf.length) return 0
    return withConf.reduce((s, d) => s + (d.classification_confidence ?? 0), 0) / withConf.length
  })()

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Analytics</h1>
        <p className="text-slate-400 mt-1">Insights from your document corpus and conversations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total documents" value={items.length} icon={FileText} />
        <StatCard label="Avg classifier confidence" value={`${(avgConfidence * 100).toFixed(1)}%`} icon={TrendingUp} accent="text-emerald-500" />
        <StatCard label="Conversations" value={convs.length} icon={MessageSquare} accent="text-violet-500" />
        <StatCard label="Categories used" value={categoryData.length} icon={Search} accent="text-amber-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Category distribution</h2>
          {categoryData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-slate-500 text-sm">No categorized documents yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={categoryData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Processing status</h2>
          {statusData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-slate-500 text-sm">No documents yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={statusData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#94a3b8" style={{ fontSize: 12 }} />
                <YAxis stroke="#94a3b8" style={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={["#10b981", "#f59e0b", "#ef4444"][i] ?? "#6366f1"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">Upload activity</h2>
        {uploadTrend.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-500 text-sm">No uploads yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={uploadTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: 12 }} />
              <YAxis stroke="#94a3b8" style={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Line type="monotone" dataKey="uploads" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
