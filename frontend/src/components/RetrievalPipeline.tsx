import { useState } from "react"
import { ChevronDown, ChevronRight, Layers, Search, GitMerge, Sparkles } from "lucide-react"

interface Props {
  denseCount: number | null
  keywordCount: number | null
  fusedCount: number | null
  rerankedCount: number | null
  latencyMs: number | null
  useReranker: boolean
}

const STEPS = [
  {
    key: "dense",
    label: "Dense retrieval",
    desc: "MiniLM bi-encoder · pgvector cosine · top-30",
    icon: Layers,
    accent: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
  },
  {
    key: "keyword",
    label: "Keyword search",
    desc: "Postgres FTS · ts_rank_cd · top-30",
    icon: Search,
    accent: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
  },
  {
    key: "rrf",
    label: "Reciprocal Rank Fusion",
    desc: "Merge by 1/(k + rank) · k=60",
    icon: GitMerge,
    accent: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
  },
  {
    key: "rerank",
    label: "Cross-encoder reranking",
    desc: "ms-marco-MiniLM-L-6-v2 · joint query-doc scoring",
    icon: Sparkles,
    accent: "text-violet-400",
    bg: "bg-violet-500/10",
    border: "border-violet-500/20",
  },
]

export default function RetrievalPipeline(props: Props) {
  const [open, setOpen] = useState(false)

  const counts = {
    dense: props.denseCount,
    keyword: props.keywordCount,
    rrf: props.fusedCount,
    rerank: props.useReranker ? props.rerankedCount : null,
  } as const

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl mb-6">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-800/30 transition"
      >
        <div className="flex items-center gap-2 text-sm text-slate-300">
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <span className="font-medium">Retrieval pipeline</span>
          {props.latencyMs !== null && (
            <span className="text-xs text-slate-500 ml-2">· {props.latencyMs} ms total</span>
          )}
        </div>
        <span className="text-xs text-slate-500">
          {props.useReranker ? "4 stages" : "3 stages"}
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-2">
            {STEPS.map((s, i) => {
              if (s.key === "rerank" && !props.useReranker) return null
              const Icon = s.icon
              const count = counts[s.key as keyof typeof counts]
              return (
                <div
                  key={s.key}
                  className={`rounded-lg p-4 border ${s.bg} ${s.border}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={`p-1.5 rounded ${s.bg}`}>
                      <Icon className={`w-4 h-4 ${s.accent}`} />
                    </div>
                    <span className="text-xs font-mono text-slate-500">step {i + 1}</span>
                  </div>
                  <div className="text-sm font-medium text-slate-100">{s.label}</div>
                  <div className="text-xs text-slate-400 mt-1 leading-relaxed">{s.desc}</div>
                  {count !== null && (
                    <div className={`text-xs mt-2 ${s.accent}`}>
                      → {count} candidate{count !== 1 ? "s" : ""}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          <p className="text-xs text-slate-500 mt-3 leading-relaxed">
            Hybrid retrieval combines semantic (dense vector) and lexical (keyword) search,
            fuses them with Reciprocal Rank Fusion, then rescores the top-K candidates with a
            cross-encoder. This two-stage architecture gives dense retrieval's scalability
            plus cross-encoder's precision.
          </p>
        </div>
      )}
    </div>
  )
}
