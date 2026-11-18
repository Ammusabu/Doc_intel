import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeft, FileText, CheckCircle2, XCircle, Clock, AlertCircle,
  Layers, Hash, Database, ChevronDown, ChevronRight, Trash2, Download, RefreshCw,
} from "lucide-react"
import { api } from "../lib/api"
import type { DocumentOut, ChunksResponse, TextResponse } from "../lib/types"
import { categoryChip, formatBytes, formatDate, STATUS_STYLES } from "../lib/categories"

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [doc, setDoc] = useState<DocumentOut | null>(null)
  const [chunks, setChunks] = useState<ChunksResponse | null>(null)
  const [text, setText] = useState<TextResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [expandedPages, setExpandedPages] = useState<Set<number>>(new Set())
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set())
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [reprocessing, setReprocessing] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      api.get<DocumentOut>(`/documents/${id}`),
      api.get<ChunksResponse>(`/documents/${id}/chunks`),
      api.get<TextResponse>(`/documents/${id}/text`),
    ])
      .then(([d, c, t]) => { setDoc(d.data); setChunks(c.data); setText(t.data) })
      .catch((e) => setError(e?.response?.data?.detail ?? "Failed to load document"))
      .finally(() => setLoading(false))
  }, [id])

  async function onReprocess() {
    if (!doc) return
    setReprocessing(true)
    try {
      await api.post(`/documents/${doc.id}/reprocess`)
      const r = await api.get<DocumentOut>(`/documents/${doc.id}`)
      setDoc(r.data)
    } catch (e) { console.error(e) } finally { setReprocessing(false) }
  }

  async function onDelete() {
    if (!doc) return
    setDeleting(true)
    try {
      await api.delete(`/documents/${doc.id}`)
      navigate("/documents")
    } catch (e) { console.error(e) } finally { setDeleting(false) }
  }

  function togglePage(p: number) {
    setExpandedPages((prev) => {
      const n = new Set(prev)
      if (n.has(p)) n.delete(p); else n.add(p)
      return n
    })
  }

  function toggleChunk(cid: string) {
    setExpandedChunks((prev) => {
      const n = new Set(prev)
      if (n.has(cid)) n.delete(cid); else n.add(cid)
      return n
    })
  }

  if (loading) return <div className="p-8 text-slate-400">Loading document...</div>
  if (error) return <div className="p-8 text-red-400">{error}</div>
  if (!doc || !chunks || !text) return null

  const StatusIcon = doc.status === "completed" ? CheckCircle2
    : doc.status === "failed" ? XCircle
    : Clock

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <button
        onClick={() => navigate("/documents")}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 mb-4 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to documents
      </button>

      <div className="flex items-start justify-between mb-8">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <FileText className="w-8 h-8 text-brand-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100 break-words">{doc.title}</h1>
            <p className="text-sm text-slate-500 mt-1 break-all">{doc.original_filename}</p>
            <div className="flex items-center gap-2 mt-3">
              <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${STATUS_STYLES[doc.status]}`}>
                <StatusIcon className="w-3 h-3" />
                {doc.status}
              </span>
              {doc.predicted_category && (
                <span className={`text-xs px-2.5 py-1 rounded-full border ${categoryChip(doc.predicted_category)}`}>
                  {doc.predicted_category}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`${import.meta.env.VITE_API_URL}/documents/${doc.id}/download`}
            onClick={(e) => {
              e.preventDefault()
              api.get(`/documents/${doc.id}/download`, { responseType: "blob" })
                .then((r) => {
                  const url = URL.createObjectURL(r.data)
                  const a = document.createElement("a")
                  a.href = url
                  a.download = doc.original_filename
                  document.body.appendChild(a)
                  a.click()
                  a.remove()
                  URL.revokeObjectURL(url)
                })
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm border border-slate-700 transition"
          >
            <Download className="w-4 h-4" />
            Download
          </a>
          <button
            onClick={onReprocess}
            disabled={reprocessing || doc.status === "processing" || doc.status === "pending"}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600/10 hover:bg-brand-600/20 text-brand-400 text-sm border border-brand-500/20 disabled:opacity-40 transition"
          >
            <RefreshCw className={`w-4 h-4 ${reprocessing ? "animate-spin" : ""}`} />
            {reprocessing ? "Reprocessing..." : "Reprocess"}
          </button>
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600/10 hover:bg-red-600/20 text-red-400 text-sm border border-red-500/20 transition"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Layers className="w-3.5 h-3.5" />
            Chunks
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">{chunks.total}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Hash className="w-3.5 h-3.5" />
            Pages
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">{doc.page_count}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <FileText className="w-3.5 h-3.5" />
            Size
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">{formatBytes(doc.file_size_bytes)}</div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Database className="w-3.5 h-3.5" />
            Embeddings
          </div>
          <div className="text-sm font-medium text-slate-100 mt-3 truncate">
            {chunks.embedding_model ?? "—"}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Document information</h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Document ID</dt>
              <dd className="text-slate-300 font-mono text-xs break-all">{doc.id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">MIME type</dt>
              <dd className="text-slate-300 break-all">{doc.mime_type}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Uploaded</dt>
              <dd className="text-slate-300">{formatDate(doc.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Last updated</dt>
              <dd className="text-slate-300">{formatDate(doc.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Classification</h2>
          {doc.predicted_category ? (
            <>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400">Predicted category</span>
                <span className={`text-sm px-2.5 py-1 rounded-full border ${categoryChip(doc.predicted_category)}`}>
                  {doc.predicted_category}
                </span>
              </div>
              {doc.classification_confidence != null && (
                <>
                  <div className="flex items-center justify-between mt-4 mb-1">
                    <span className="text-sm text-slate-400">Confidence</span>
                    <span className="text-sm text-slate-200">
                      {(doc.classification_confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-500"
                      style={{ width: `${doc.classification_confidence * 100}%` }}
                    />
                  </div>
                </>
              )}
              <p className="text-xs text-slate-500 mt-4">
                Predicted by fine-tuned DistilBERT classifier using full document text
                (first ~6 chunks ≈ 1,500 tokens).
              </p>
            </>
          ) : (
            <p className="text-slate-500 text-sm">Not yet classified.</p>
          )}
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100">Processing history</h2>
          <span className="text-xs text-slate-500">inferred from timestamps</span>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
            <span className="text-slate-300">Uploaded</span>
            <span className="text-slate-500 ml-auto">{formatDate(doc.created_at)}</span>
          </div>
          {doc.status === "completed" && (
            <>
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                <span className="text-slate-300">Text extracted &amp; chunked ({chunks.total} chunks)</span>
                <span className="text-slate-500 ml-auto">{formatDate(doc.updated_at)}</span>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                <span className="text-slate-300">
                  Classified as <span className="text-brand-400">{doc.predicted_category}</span>
                  {doc.classification_confidence != null &&
                    ` (${(doc.classification_confidence * 100).toFixed(1)}% confidence)`}
                </span>
                <span className="text-slate-500 ml-auto">{formatDate(doc.updated_at)}</span>
              </div>
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                <span className="text-slate-300">
                  {chunks.total} chunks embedded with <span className="font-mono text-xs">{chunks.embedding_model}</span> v{chunks.embedding_version}
                </span>
                <span className="text-slate-500 ml-auto">{formatDate(doc.updated_at)}</span>
              </div>
            </>
          )}
          {doc.status === "processing" && (
            <div className="flex items-center gap-3">
              <Clock className="w-4 h-4 text-yellow-500 flex-shrink-0 animate-pulse" />
              <span className="text-slate-300">Processing in background...</span>
            </div>
          )}
          {doc.status === "pending" && (
            <div className="flex items-center gap-3">
              <Clock className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              <span className="text-slate-300">Queued for processing</span>
            </div>
          )}
          {doc.status === "failed" && (
            <div className="flex items-center gap-3">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <span className="text-red-300">Processing failed: {doc.error_message}</span>
            </div>
          )}
        </div>
      </div>

      {chunks.total > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Generated chunks ({chunks.total})</h2>
          <div className="space-y-2">
            {chunks.chunks.map((c) => {
              const open = expandedChunks.has(c.id)
              return (
                <div key={c.id} className="border border-slate-800 rounded-lg overflow-hidden">
                  <button
                    onClick={() => toggleChunk(c.id)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/50 text-left transition"
                  >
                    {open ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
                    <span className="text-sm font-medium text-slate-300">Chunk #{c.chunk_index}</span>
                    <span className="text-xs text-slate-500">page {c.page_number} · {c.token_count} tokens</span>
                    <span className={`ml-auto text-xs px-2 py-0.5 rounded-full border ${
                      c.has_embedding
                        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                        : "bg-slate-500/10 text-slate-400 border-slate-500/20"
                    }`}>
                      {c.has_embedding ? "✓ embedded" : "no embedding"}
                    </span>
                  </button>
                  {open && (
                    <div className="px-4 py-3 bg-slate-950/50 border-t border-slate-800">
                      <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{c.content}</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {text.text_by_page.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">Extracted text</h2>
          <div className="space-y-2">
            {text.text_by_page.map((p) => {
              const open = expandedPages.has(p.page_number)
              return (
                <div key={p.page_number} className="border border-slate-800 rounded-lg overflow-hidden">
                  <button
                    onClick={() => togglePage(p.page_number)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/50 text-left transition"
                  >
                    {open ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
                    <span className="text-sm font-medium text-slate-300">Page {p.page_number}</span>
                    <span className="text-xs text-slate-500">{p.text.length} chars</span>
                  </button>
                  {open && (
                    <div className="px-4 py-3 bg-slate-950/50 border-t border-slate-800 max-h-96 overflow-auto">
                      <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed font-mono">{p.text}</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {confirmDelete && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setConfirmDelete(false)}>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-100 mb-2">Delete document?</h3>
            <p className="text-sm text-slate-400 mb-4">This permanently removes the file, all chunks, and embeddings. Cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(false)} className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm">Cancel</button>
              <button onClick={onDelete} disabled={deleting} className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm">
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
