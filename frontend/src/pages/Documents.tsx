import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Trash2, Filter, ArrowUpDown, Eye, Download, RefreshCw,
} from "lucide-react"
import { api } from "../lib/api"
import type { DocumentListOut, DocumentOut, SortKey, SortDir } from "../lib/types"
import UploadZone from "../components/UploadZone"
import { categoryChip, formatBytes, formatDate, STATUS_STYLES } from "../lib/categories"

const CATEGORIES = ["", "Technical", "Finance", "General", "HR", "Legal", "Research", "Business"]
const STATUSES = ["", "completed", "processing", "pending", "failed"]

type DateWindow = "" | "7" | "30" | "90"

export default function Documents() {
  const navigate = useNavigate()
  const [data, setData] = useState<DocumentListOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("")
  const [dateWindow, setDateWindow] = useState<DateWindow>("")
  const [sortKey, setSortKey] = useState<SortKey>("created_at")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const [confirmDelete, setConfirmDelete] = useState<DocumentOut | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [reprocessingId, setReprocessingId] = useState<string | null>(null)

  async function load() {
    try {
      const params = new URLSearchParams({ page: "1", page_size: "100" })
      if (statusFilter) params.set("status", statusFilter)
      const res = await api.get<DocumentListOut>(`/documents?${params.toString()}`)
      setData(res.data)
    } catch (e) { console.error(e) } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [statusFilter])

  useEffect(() => {
    const anyInProgress = data?.items.some(
      (d) => d.status === "pending" || d.status === "processing"
    )
    if (!anyInProgress) return
    const iv = setInterval(load, 2000)
    return () => clearInterval(iv)
  }, [data])

  const filtered = useMemo(() => {
    let items = [...(data?.items ?? [])]

    if (categoryFilter) {
      items = items.filter((d) => d.predicted_category === categoryFilter)
    }

    if (dateWindow) {
      const n = parseInt(dateWindow, 10)
      const cutoff = Date.now() - n * 24 * 60 * 60 * 1000
      items = items.filter((d) => new Date(d.created_at).getTime() >= cutoff)
    }

    items.sort((a, b) => {
      let av: number | string | null
      let bv: number | string | null
      if (sortKey === "created_at") {
        av = new Date(a.created_at).getTime()
        bv = new Date(b.created_at).getTime()
      } else if (sortKey === "file_size_bytes") {
        av = a.file_size_bytes
        bv = b.file_size_bytes
      } else {
        av = a.classification_confidence ?? -1
        bv = b.classification_confidence ?? -1
      }
      if (av === bv) return 0
      const cmp = (av as number) > (bv as number) ? 1 : -1
      return sortDir === "asc" ? cmp : -cmp
    })

    return items
  }, [data, categoryFilter, dateWindow, sortKey, sortDir])

  async function onDelete(doc: DocumentOut) {
    setDeleting(true)
    try {
      await api.delete(`/documents/${doc.id}`)
      setConfirmDelete(null)
      await load()
    } catch (e) { console.error(e) } finally { setDeleting(false) }
  }

  async function onReprocess(doc: DocumentOut) {
    setReprocessingId(doc.id)
    try {
      await api.post(`/documents/${doc.id}/reprocess`)
      await load()
    } catch (e) { console.error(e) } finally { setReprocessingId(null) }
  }

  async function onDownload(doc: DocumentOut) {
    try {
      const r = await api.get(`/documents/${doc.id}/download`, { responseType: "blob" })
      const url = URL.createObjectURL(r.data)
      const a = document.createElement("a")
      a.href = url
      a.download = doc.original_filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) { console.error(e) }
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("desc")
    }
  }

  const SortIcon = ({ k }: { k: SortKey }) => (
    <ArrowUpDown className={`w-3 h-3 ml-1 inline ${sortKey === k ? "text-brand-500" : "text-slate-600"}`} />
  )

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100">Documents</h1>
        <p className="text-slate-400 mt-1">Upload, manage, and inspect your documents</p>
      </div>

      <div className="mb-6">
        <UploadZone onUploaded={load} />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex flex-wrap items-center gap-3">
          <div className="text-sm text-slate-300 mr-auto">
            {loading ? "Loading..." : `${filtered.length} of ${data?.total ?? 0} document${(data?.total ?? 0) !== 1 ? "s" : ""}`}
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Filter className="w-4 h-4 text-slate-500" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200"
            >
              {CATEGORIES.map((c) => <option key={c} value={c}>{c || "All categories"}</option>)}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200"
            >
              {STATUSES.map((s) => <option key={s} value={s}>{s || "All statuses"}</option>)}
            </select>
            <select
              value={dateWindow}
              onChange={(e) => setDateWindow(e.target.value as DateWindow)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="">Any date</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading documents...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-slate-400">No documents match your filters</div>
            <div className="text-sm text-slate-500 mt-1">Try clearing the filters above</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-800/50">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Title</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Category</th>
                <th className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3">Status</th>
                <th
                  onClick={() => toggleSort("file_size_bytes")}
                  className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3 cursor-pointer hover:text-slate-200"
                >
                  Size <SortIcon k="file_size_bytes" />
                </th>
                <th
                  onClick={() => toggleSort("classification_confidence")}
                  className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3 cursor-pointer hover:text-slate-200"
                >
                  Confidence <SortIcon k="classification_confidence" />
                </th>
                <th
                  onClick={() => toggleSort("created_at")}
                  className="text-left text-xs font-medium text-slate-400 uppercase px-4 py-3 cursor-pointer hover:text-slate-200"
                >
                  Uploaded <SortIcon k="created_at" />
                </th>
                <th className="text-right text-xs font-medium text-slate-400 uppercase px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr
                  key={d.id}
                  onClick={() => navigate(`/documents/${d.id}`)}
                  className="border-t border-slate-800 hover:bg-slate-800/30 cursor-pointer transition"
                >
                  <td className="px-4 py-3">
                    <div className="text-sm text-slate-200 truncate max-w-md">{d.title}</div>
                  </td>
                  <td className="px-4 py-3">
                    {d.predicted_category ? (
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${categoryChip(d.predicted_category)}`}>
                        {d.predicted_category}
                      </span>
                    ) : <span className="text-xs text-slate-500">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLES[d.status]}`}>
                      {d.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">{formatBytes(d.file_size_bytes)}</td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {d.classification_confidence != null
                      ? `${(d.classification_confidence * 100).toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">{formatDate(d.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => navigate(`/documents/${d.id}`)}
                        title="Preview"
                        className="p-1.5 rounded hover:bg-slate-700 text-slate-500 hover:text-slate-200 transition"
                      ><Eye className="w-4 h-4" /></button>
                      <button
                        onClick={() => onDownload(d)}
                        title="Download"
                        className="p-1.5 rounded hover:bg-slate-700 text-slate-500 hover:text-slate-200 transition"
                      ><Download className="w-4 h-4" /></button>
                      <button
                        onClick={() => onReprocess(d)}
                        disabled={reprocessingId === d.id || d.status === "processing" || d.status === "pending"}
                        title="Reprocess"
                        className="p-1.5 rounded hover:bg-slate-700 text-slate-500 hover:text-slate-200 disabled:opacity-40 transition"
                      ><RefreshCw className={`w-4 h-4 ${reprocessingId === d.id ? "animate-spin" : ""}`} /></button>
                      <button
                        onClick={() => setConfirmDelete(d)}
                        title="Delete"
                        className="p-1.5 rounded hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition"
                      ><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {confirmDelete && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setConfirmDelete(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-slate-100 mb-2">Delete document?</h3>
            <p className="text-sm text-slate-400 mb-1">Permanently remove:</p>
            <p className="text-sm text-slate-200 mb-4 font-medium break-words">{confirmDelete.title}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(null)} className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm">Cancel</button>
              <button onClick={() => onDelete(confirmDelete)} disabled={deleting} className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm">
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
