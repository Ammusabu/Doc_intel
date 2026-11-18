const COLORS: Record<string, string> = {
  Technical: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  Finance:   "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  General:   "bg-slate-500/20 text-slate-300 border-slate-500/30",
  HR:        "bg-pink-500/20 text-pink-300 border-pink-500/30",
  Legal:     "bg-amber-500/20 text-amber-300 border-amber-500/30",
  Research:  "bg-violet-500/20 text-violet-300 border-violet-500/30",
  Business:  "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
}

export function categoryChip(category: string | null): string {
  if (!category) return "bg-slate-500/20 text-slate-300 border-slate-500/30"
  return COLORS[category] ?? COLORS.General
}

export const STATUS_STYLES: Record<string, string> = {
  pending:    "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  processing: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  completed:  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  failed:     "bg-red-500/20 text-red-300 border-red-500/30",
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  })
}
