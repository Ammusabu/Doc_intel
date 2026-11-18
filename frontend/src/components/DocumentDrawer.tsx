import { X, FileText, CheckCircle2, XCircle, Clock } from "lucide-react"
import type { DocumentOut } from "../lib/types"
import { categoryChip, formatBytes, formatDate, STATUS_STYLES } from "../lib/categories"

interface Props {
  doc: DocumentOut
  onClose: () => void
}

export default function DocumentDrawer({ doc, onClose }: Props) {
  const Icon = doc.status === "completed" ? CheckCircle2
    : doc.status === "failed" ? XCircle
    : Clock

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-slate-900 border-l border-slate-800 z-50 overflow-auto">
        <div className="sticky top-0 bg-slate-900 border-b border-slate-800 p-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-100">Document details</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-800 text-slate-400">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-5">
          <div className="flex items-start gap-3">
            <div className="p-3 rounded-lg bg-slate-800">
              <FileText className="w-6 h-6 text-brand-500" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-100 break-words">{doc.title}</div>
              <div className="text-xs text-slate-500 mt-1 break-all">{doc.original_filename}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">Status</div>
              <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border ${STATUS_STYLES[doc.status]}`}>
                <Icon className="w-3 h-3" />
                {doc.status}
              </span>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500 mb-1">Category</div>
              {doc.predicted_category ? (
                <span className={`text-xs px-2 py-1 rounded-full border ${categoryChip(doc.predicted_category)}`}>
                  {doc.predicted_category}
                </span>
              ) : (
                <span className="text-xs text-slate-500">—</span>
              )}
            </div>
          </div>

          {doc.classification_confidence != null && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-slate-500">Classification confidence</div>
                <div className="text-xs text-slate-300">{(doc.classification_confidence * 100).toFixed(1)}%</div>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500"
                  style={{ width: `${doc.classification_confidence * 100}%` }}
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500">Size</div>
              <div className="text-sm text-slate-200 mt-1">{formatBytes(doc.file_size_bytes)}</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <div className="text-xs text-slate-500">Pages</div>
              <div className="text-sm text-slate-200 mt-1">{doc.page_count}</div>
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-500">MIME type</div>
            <div className="text-sm text-slate-200 mt-1 break-all">{doc.mime_type}</div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-500">Uploaded</div>
            <div className="text-sm text-slate-200 mt-1">{formatDate(doc.created_at)}</div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-500">Document ID</div>
            <div className="text-xs text-slate-400 font-mono mt-1 break-all">{doc.id}</div>
          </div>

          {doc.error_message && (
            <div className="bg-red-950/30 border border-red-900 rounded-lg p-3">
              <div className="text-xs text-red-400">Processing error</div>
              <div className="text-sm text-red-300 mt-1">{doc.error_message}</div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
