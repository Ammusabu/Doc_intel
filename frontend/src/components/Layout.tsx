import { NavLink, Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import {
  LayoutDashboard, FileText, Search, MessageSquare, BarChart3, LogOut, Sparkles,
} from "lucide-react"

const NAV = [
  { to: "/dashboard",  label: "Dashboard",  icon: LayoutDashboard },
  { to: "/documents",  label: "Documents",  icon: FileText },
  { to: "/search",     label: "Search",     icon: Search },
  { to: "/chat",       label: "AI Chat",    icon: MessageSquare },
  { to: "/analytics",  label: "Analytics",  icon: BarChart3 },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="flex h-screen bg-slate-950">
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-800">
          <Sparkles className="w-6 h-6 text-brand-500 mr-2" />
          <span className="font-bold text-lg text-slate-100">DocIntel</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-brand-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                }`
              }
            >
              <item.icon className="w-4 h-4 mr-3" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-slate-800">
          <div className="px-3 py-2 text-xs text-slate-500 truncate">
            {user?.email}
          </div>
          <button
            onClick={() => { logout(); navigate("/login") }}
            className="flex items-center w-full px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
          >
            <LogOut className="w-4 h-4 mr-3" />
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
