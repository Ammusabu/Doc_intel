import { useEffect, useState } from "react"
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, LineChart, Line,
} from "recharts"
import {
  FileText, CheckCircle2, XCircle, Clock, TrendingUp, Brain, Search as SearchIcon,
  MessageSquare, Activity, AlertCircle, Loader2,
} from "lucide-react"
import { api } from "../lib/api"
import StatCard from "../components/StatCard"

interface AnalyticsData {
  documents: {
    total: number
    completed: number
    processing: number
    failed: number
    success_rate: number
    category_distribution: { name: string; value: number }[]
    upload_trend: { date: string; uploads: number }[]
  }
  dl_performance: {
    avg_confidence: number
    confidence_distribution: { bucket: string; count: number }[]
    category_confidence: { category: string; avg: number; count: number }[]
  }
  retrieval: {
    total_searches: number
    avg_latency_ms: number
    total_chunks_retrievable: number
  }
  rag: {
    total_questions: number
    questions_with_citations: number
    no_relevant_docs: number
    citation_rate: number
  }
}

const COLORS = ["#6255ED", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#06B6D4", "#64748B"]

const TOOLTIP_STYLE = {
  backgroundColor: "#111B2E",
  border: "1px solid #26334A",
  borderRadius: "8px",
  color: "#E2E8F0",
  fontSize: "12px",
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-slate-100">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {children}
    </section>
  )
}

function ChartCard({ title, children, tooltip }: { title: string; children: React.ReactNode; tooltip?: string }) {
  return (
    <div className="bg-[#111B2E] border border-[#26334A] rounded-xl p-5 hover:border-[#2F3E56] transition">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-200">{title}</h3>
        {tooltip && (
          <span className="text-xs text-slate-500 cursor-help" title={tooltip}>ⓘ</span>
        )}
      </div>
      {children}
    </div>
  )
}

function Skeleton({ h = 280 }: { h?: number }) {
  return (
    <div className="bg-[#111B2E] border border-[#26334A] rounded-xl p-5 animate-pulse" style={{ height: h + 50 }}>
      <div className="h-4 w-32 bg-slate-800 rounded mb-4" />
      <div className="h-full bg-slate-800/50 rounded" />
    </div>
  )
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    api.get<AnalyticsData>("/analytics/summary")
      .then((r) => setData(r.data))
      .catch((e) => setError(e?.response?.data?.detail ?? "Failed to load analytics"))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-100 mb-8">Analytics</h1>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="h-32 bg-[#111B2E] border border-[#26334A] rounded-xl animate-pulse" />
          <div className="h-32 bg-[#111B2E] border border-[#26334A] rounded-xl animate-pulse" />
          <div className="h-32 bg-[#111B2E] border border-[#26334A] rounded-xl animate-pulse" />
          <div className="h-32 bg-[#111B2E] border border-[#26334A] rounded-xl animate-pulse" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton />
          <Skeleton />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="bg-red-950/30 border border-red-900 rounded-xl p-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-red-200 font-medium">Could not load analytics</div>
            <div className="text-sm text-red-300 mt-1">{error}</div>
          </div>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { documents, dl_performance, retrieval, rag } = data
  const lowConfidence = dl_performance.avg_confidence < 0.5

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-slate-100">Analytics</h1>
        <p className="text-slate-400 mt-1">Document intelligence, model performance, retrieval quality</p>
      </div>

      <Section
        title="Document analytics"
        subtitle="Upload volume, processing health, and category distribution"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard label="Total documents" value={documents.total} icon={FileText} />
          <StatCard label="Completed" value={documents.completed} icon={CheckCircle2} accent="text-emerald-500" />
          <StatCard label="Processing" value={documents.processing} icon={Clock} accent="text-yellow-500" />
          <StatCard label="Failed" value={documents.failed} icon={XCircle} accent="text-red-500" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartCard title="Category distribution" tooltip="Documents grouped by classifier's predicted category">
            {documents.category_distribution.length === 0 ? (
              <div className="h-80 flex items-center justify-center text-slate-500 text-sm">No categorized documents yet</div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie
                    data={documents.category_distribution}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    innerRadius={50}
                    paddingAngle={2}
                    label={(e: any) => `${e.name} (${e.value})`}
                    labelLine={{ stroke: "#64748B" }}
                  >
                    {documents.category_distribution.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard title="Upload trend (last 14 days)" tooltip="Daily document uploads">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={documents.upload_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#26334A" />
                <XAxis dataKey="date" stroke="#94A3B8" style={{ fontSize: 11 }} />
                <YAxis stroke="#94A3B8" style={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Line type="monotone" dataKey="uploads" stroke="#6255ED" strokeWidth={2.5} dot={{ r: 3, fill: "#6255ED" }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </Section>

      <Section
        title="Deep learning performance"
        subtitle="DistilBERT classifier output distribution"
      >
        {lowConfidence && (
          <div className="bg-amber-950/30 border border-amber-800/50 rounded-xl p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <div className="text-amber-200 font-medium">Average confidence is below 50%</div>
              <div className="text-amber-300/80 mt-1">
                The classifier is uncertain on this corpus. This is expected when documents
                differ from training data (20 Newsgroups). Confidence is <strong>not</strong> accuracy —
                low confidence means the model is hedging, not necessarily wrong.
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <StatCard label="Avg confidence" value={`${(dl_performance.avg_confidence * 100).toFixed(1)}%`} icon={Brain} accent="text-violet-500" />
          <StatCard label="Success rate" value={`${documents.success_rate}%`} icon={CheckCircle2} accent="text-emerald-500" />
          <StatCard label="Categories used" value={dl_performance.category_confidence.length} icon={TrendingUp} accent="text-amber-500" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartCard title="Confidence distribution" tooltip="How confident the classifier is on each document">
            {dl_performance.confidence_distribution.every((b) => b.count === 0) ? (
              <div className="h-80 flex items-center justify-center text-slate-500 text-sm">No classified documents yet</div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={dl_performance.confidence_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#26334A" />
                  <XAxis dataKey="bucket" stroke="#94A3B8" style={{ fontSize: 11 }} />
                  <YAxis stroke="#94A3B8" style={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                    {dl_performance.confidence_distribution.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard title="Category-wise confidence" tooltip="Average classifier confidence per predicted category">
            {dl_performance.category_confidence.length === 0 ? (
              <div className="h-80 flex items-center justify-center text-slate-500 text-sm">No data</div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={dl_performance.category_confidence} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#26334A" />
                  <XAxis type="number" domain={[0, 1]} stroke="#94A3B8" style={{ fontSize: 11 }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                  <YAxis type="category" dataKey="category" stroke="#94A3B8" style={{ fontSize: 11 }} width={80} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: any) => `${(v * 100).toFixed(1)}%`} />
                  <Bar dataKey="avg" radius={[0, 8, 8, 0]}>
                    {dl_performance.category_confidence.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>
        </div>

        <div className="mt-4 text-xs text-slate-500 max-w-3xl leading-relaxed">
          <strong className="text-slate-400">Note:</strong> The classifier was fine-tuned on 20 Newsgroups (1990s
          newsgroup posts). Real academic PDFs differ from that distribution, producing lower confidence scores.
          Held-out evaluation on the training distribution showed <strong className="text-slate-300">76.4% test accuracy / 0.759 macro-F1</strong>;
          confidence on out-of-distribution documents is expected to be lower without retraining on domain data.
        </div>
      </Section>

      <Section
        title="Retrieval analytics"
        subtitle="Search usage and performance"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <StatCard label="Total searches" value={retrieval.total_searches} icon={SearchIcon} />
          <StatCard label="Avg latency" value={`${retrieval.avg_latency_ms} ms`} icon={Activity} accent="text-emerald-500" />
          <StatCard label="Retrievable chunks" value={retrieval.total_chunks_retrievable} icon={FileText} accent="text-cyan-500" />
        </div>
      </Section>

      <Section
        title="RAG analytics"
        subtitle="Question answering quality"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total questions" value={rag.total_questions} icon={MessageSquare} />
          <StatCard label="With citations" value={rag.questions_with_citations} icon={CheckCircle2} accent="text-emerald-500" />
          <StatCard label="Citation rate" value={`${rag.citation_rate}%`} icon={TrendingUp} accent="text-violet-500" />
          <StatCard label="No relevant docs" value={rag.no_relevant_docs} icon={XCircle} accent="text-yellow-500" />
        </div>
      </Section>
    </div>
  )
}
