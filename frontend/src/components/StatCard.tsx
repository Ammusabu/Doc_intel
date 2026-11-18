import type { LucideIcon } from "lucide-react"

interface Props {
  label: string
  value: string | number
  icon: LucideIcon
  accent?: string
}

export default function StatCard({ label, value, icon: Icon, accent = "text-brand-500" }: Props) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-slate-400">{label}</div>
          <div className="text-3xl font-bold text-slate-100 mt-2">{value}</div>
        </div>
        <div className={`p-2 rounded-lg bg-slate-800 ${accent}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}
