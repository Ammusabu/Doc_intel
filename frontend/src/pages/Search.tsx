import { useEffect, useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Search as SearchIcon, Loader2, FileText, ExternalLink, X, Clock, Sparkles } from "lucide-react"
import { api } from "../lib/api"
import type { SearchResult } from "../lib/types"
import { categoryChip } from "../lib/categories"
import RetrievalPipeline from "../components/RetrievalPipeline"
import { highlight } from "../lib/highlight"
import { getRecentSearches, addRecentSearch, clearRecentSearches } from "../lib/recentSearches"

interface SearchResponse {
  query: string
  latency_ms: number
  results: SearchResult[]
}

const SUGGESTIONS = [
  "graphics driver troubleshooting",
  "quarterly revenue growth",
  "paid time off policy",
  "DistilBERT accuracy",
  "GDPR data protection",
  "parental leave duration",
]

const CATEGORIES = ["", "Technical", "Finance", "General", "HR", "Legal", "Research", "Business"]

export default function Search() {
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("")
  const [useReranker, setUseReranker] = useState(true)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [error, setError] = useState("")
  const [recent, setRecent] = useState<string[]>(getRecentSearches())
  const [lastQuery, setLastQuery] = useState("")

  useEffect(() => {
    setRecent(getRecentSearches())
  }, [])

  async function runSearch(q: string) {
    if (!q.trim()) return
    setQuery(q)
    setLastQuery(q)
    setLoading(true); setError(""); setResponse(null)
    addRecentSearch(q)
    setRecent(getRecentSearches())
    try {
      const res = await api.post<SearchResponse>("/search", {
        query: q.trim(),
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

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    runSearch(query)
  }

  function clearRecent() {
    clearRecentSearches()
    setRecent([])
  }

  const semanticHits = response?.results.filter((r) => (r.dense_score ?? 0) > 0).length ?? 0
  const keywordHits = response?.results.filter((r) => (r.keyword_score ?? 0) > 0).length ?? 0

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-100">Search</h1>
        <p className="text-slate-400 mt-1">
          Hybrid retrieval — semantic vectors + keyword search + cross-encoder reranking
        </p>
      </div>

      <form onSubmit={onSubmit} className="mb-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question or search for keywords..."
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

      {recent.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-slate-500">
            <Clock className="w-3.5 h-3.5" />
            Recent:
          </span>
          {recent.slice(0, 6).map((q) => (
            <button
              key={q}
              onClick={() => runSearch(q)}
              className="text-xs px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            >
              {q}
            </button>
          ))}
          <button
            onClick={clearRecent}
            className="text-xs text-slate-500 hover:text-slate-300 ml-1"
          >
            clear
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-950/50 border border-red-900 text-red-300 rounded-lg p-4 mb-4">{error}</div>
      )}

      {response && (
        <>
          <div className="flex items-center justify-between mb-3 text-sm text-slate-400">
            <div>
              {response.results.length} result{response.results.length !== 1 ? "s" : ""} for{" "}
              <span className="text-slate-200">&quot;{response.query}&quot;</span>
            </div>
            <div className="flex items-center gap-3 text-xs">
              {semanticHits > 0 && (
                <span className="flex items-center gap-1 text-blue-400">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  {semanticHits} semantic
                </span>
              )}
              {keywordHits > 0 && (
                <span className="flex items-center gap-1 text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  {keywordHits} keyword
                </span>
              )}
            </div>
          </div>

          <RetrievalPipeline
            denseCount={semanticHits}
            keywordCount={keywordHits}
            fusedCount={response.results.length}
            rerankedCount={useReranker ? response.results.length : null}
            latencyMs={response.latency_ms}
            useReranker={useReranker}
          />

          {response.results.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
              <div className="text-slate-400">No matches found</div>
              <div className="text-sm text-slate-500 mt-1">Try a different query or upload more documents</div>
            </div>
          ) : (
            <div className="space-y-3">
              {response.results.map((r) => {
                const fragments = highlight(r.content, lastQuery)
                const semStrong = (r.dense_score ?? 0) > (r.keyword_score ?? 0)
                return (
                  <div
                    key={r.chunk_id}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition"
                  >
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <div className="p-1.5 rounded bg-brand-500/10 flex-shrink-0">
                          <FileText className="w-4 h-4 text-brand-500" />
                        </div>
                        <div className="min-w-0">
                          <button
                            onClick={() => navigate(`/documents/${r.document_id}`)}
                            className="text-sm font-medium text-slate-200 hover:text-brand-400 truncate text-left transition"
                          >
                            {r.document_title}
                          </button>
                          <div className="text-xs text-slate-500">
                            Page {r.page_number} · chunk #{r.chunk_index} · rank #{r.final_rank}
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => navigate(`/documents/${r.document_id}`)}
                        className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex-shrink-0"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Open
                      </button>
                    </div>

                    <p className="text-sm text-slate-300 leading-relaxed line-clamp-5">
                      {fragments.map((f, i) =>
                        f.match ? (
                          <mark key={i} className="bg-amber-500/30 text-amber-100 px-0.5 rounded">
                            {f.text}
                          </mark>
                        ) : (
                          <span key={i}>{f.text}</span>
                        )
                      )}
                    </p>

                    <div className="flex flex-wrap gap-2 mt-3 text-xs">
                      {r.dense_score !== null && (
                        <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
                          semStrong
                            ? "bg-blue-500/15 text-blue-300 border-blue-500/30"
                            : "bg-blue-500/5 text-blue-400/70 border-blue-500/15"
                        }`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                          semantic: {r.dense_score.toFixed(3)}
                        </span>
                      )}
                      {r.keyword_score !== null && (
                        <span className={`px-2 py-0.5 rounded border flex items-center gap-1 ${
                          !semStrong
                            ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                            : "bg-emerald-500/5 text-emerald-400/70 border-emerald-500/15"
                        }`}>
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          keyword: {r.keyword_score.toFixed(4)}
                        </span>
                      )}
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        RRF: {r.rrf_score.toFixed(4)}
                      </span>
                      {r.rerank_score !== null && (
                        <span className="px-2 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30">
                          rerank: {r.rerank_score.toFixed(3)}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {!response && !loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-10">
          <div className="text-center mb-6">
            <SearchIcon className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <div className="text-slate-300 font-medium">Search your documents</div>
            <div className="text-sm text-slate-500 mt-1">Try one of these queries to get started</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-w-2xl mx-auto">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => runSearch(s)}
                className="flex items-center gap-2 text-left text-sm px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-800 text-slate-300 transition"
              >
                <Sparkles className="w-3.5 h-3.5 text-brand-500 flex-shrink-0" />
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
