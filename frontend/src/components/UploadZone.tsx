import { useState, useRef, type DragEvent, type ChangeEvent } from "react"
import { Upload, FileText, Loader2 } from "lucide-react"
import { api } from "../lib/api"
import { formatBytes } from "../lib/categories"

interface Props {
  onUploaded: () => void
}

export default function UploadZone({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const [progress, setProgress] = useState<string>("")
  const inputRef = useRef<HTMLInputElement>(null)

  function validate(file: File): string | null {
    const ok = [".pdf", ".docx", ".txt"]
    const ext = "." + file.name.split(".").pop()?.toLowerCase()
    if (!ok.includes(ext)) return `Unsupported file type. Use PDF, DOCX, or TXT.`
    if (file.size > 25 * 1024 * 1024) return `File too large (max 25 MB).`
    return null
  }

  async function upload(file: File) {
    const err = validate(file)
    if (err) { setError(err); return }
    setError("")
    setUploading(true)
    setProgress(`Uploading ${file.name} (${formatBytes(file.size)})...`)
    try {
      const form = new FormData()
      form.append("file", file)
      await api.post("/documents", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      setProgress("Upload complete — processing in background")
      onUploaded()
      setTimeout(() => setProgress(""), 2000)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(typeof detail === "string" ? detail : "Upload failed")
      setProgress("")
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0])
  }

  function onSelect(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.[0]) upload(e.target.files[0])
  }

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
          dragging
            ? "border-brand-500 bg-brand-500/5"
            : "border-slate-700 hover:border-slate-600 bg-slate-900/50"
        } ${uploading ? "opacity-60 cursor-wait" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={onSelect}
          disabled={uploading}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
            <div className="text-sm text-slate-300">{progress}</div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="p-3 rounded-full bg-brand-500/10">
              {dragging ? <FileText className="w-6 h-6 text-brand-500" /> : <Upload className="w-6 h-6 text-brand-500" />}
            </div>
            <div>
              <div className="text-sm font-medium text-slate-200">
                {dragging ? "Drop file to upload" : "Drag & drop a document"}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                or click to browse · PDF, DOCX, TXT · max 25 MB
              </div>
            </div>
          </div>
        )}
      </div>
      {error && (
        <div className="mt-3 text-red-400 text-sm bg-red-950/50 border border-red-900 rounded-lg p-3">
          {error}
        </div>
      )}
    </div>
  )
}
