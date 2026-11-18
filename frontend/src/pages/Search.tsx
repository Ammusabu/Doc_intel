import { useState, type FormEvent } from "react"
import { Search as SearchIcon, Loader2, FileText, ChevronRight } from "lucide-react"
import { api } from "../lib/api"
import type { SearchResult } from "../lib/types"
import { categoryChip } from "../lib/categories"

interface SearchResponse {
  query: string
  latency_ms: number
  results: SearchResult[]
}

const CATEGORIES = ["", "Technical", "Finance", "General", "HR", "Legal", "Research", "Business"]

export default function Search() {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("")
  const [useReranker, setUseReranker] = useState(true)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [error, setError] = useState("")

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true); setError(""); setResponse(null)
    try {
      const res = await api.post<SearchResponse>("/search", {
        query: query.trim(),
        top_k: 10,
        category: category || null,
        use_reranker: useReranker,
      })
      setResponse(res.data)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(typeof detail === "string" ? detail : "Search failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Search</h1>
        <p className="text-slate-400 mt-1">Hybrid retrieval — dense vectors + keyword search + RRF + cross-encoder reranking</p>
      </div>

      <form onSubmit={onSubmit} className="mb-6">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a natural-language question or search for keywords..."
              className="w-full pl-10 pr-4 py-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium transition flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Search
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-4 mt-3 text-sm">
          <div className="flex items-center gap-2">
            <label className="text-slate-400">Category:</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c || "All categories"}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={useReranker}
              onChange={(e) => setUseReranker(e.target.checked)}
              className="rounded"
            />
            Cross-encoder reranking
          </label>
        </div>
      </form>

      {error && (
        <div className="bg-red-950/50 border border-red-900 text-red-300 rounded-lg p-4 mb-4">{error}</div>
      )}

      {response && (
        <>
          <div className="flex items-center justify-between mb-4 text-sm text-slate-400">
            <span>
              {response.results.length} result{response.results.length !== 1 ? "s" : ""} for &quot;{response.query}&quot;
            </span>
            <span>{response.latency_ms} ms</span>
          </div>

          {response.results.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
              <div className="text-slate-400">No matches found</div>
              <div className="text-sm text-slate-500 mt-1">Try a different query or upload more documents</div>
            </div>
          ) : (
            <div className="space-y-3">
              {response.results.map((r) => (
                <div key={r.chunk_id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <div className="p-1.5 rounded bg-brand-500/10">
                        <FileText className="w-4 h-4 text-brand-500" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-slate-200 truncate">{r.document_title}</div>
                        <div className="text-xs text-slate-500">
                          Page {r.page_number} · chunk #{r.chunk_index} · rank #{r.final_rank}
                        </div>
                      </div>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                      RRF {r.rrf_score.toFixed(4)}
                    </span>
                  </div>

                  <p className="text-sm text-slate-300 leading-relaxed line-clamp-4">
                    {r.content}
                  </p>

                  <div className="flex flex-wrap gap-2 mt-3 text-xs">
                    {r.dense_score !== null && (
                      <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20">
                        dense: {r.dense_score.toFixed(3)}
                      </span>
                    )}
                    {r.keyword_score !== null && (
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                        keyword: {r.keyword_score.toFixed(4)}
                      </span>
                    )}
                    {r.rerank_score !== null && (
                      <span className="px-2 py-0.5 rounded bg-violet-500/10 text-violet-300 border border-violet-500/20">
                        rerank: {r.rerank_score.toFixed(3)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!response && !loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <SearchIcon className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <div className="text-slate-400">Enter a query above to search your documents</div>
          <div className="text-sm text-slate-500 mt-1">Try: &quot;graphics driver troubleshooting&quot; or &quot;quarterly revenue&quot;</div>
        </div>
      )}
    </div>
  )
}
