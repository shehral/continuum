"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"
import { signOut, useSession } from "next-auth/react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"

const navigation = [
  { name: "Dashboard", href: "/", icon: "🏠" },
  { name: "Add Knowledge", href: "/add", icon: "🧠" },
  { name: "Knowledge Graph", href: "/graph", icon: "🔗" },
  { name: "Decisions", href: "/decisions", icon: "📋" },
  { name: "Search", href: "/search", icon: "🔍" },
]

export function Sidebar() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { data: session } = useSession()

  return (
    <div className="flex h-full w-64 flex-col border-r border-white/[0.06] bg-slate-900/95 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-teal-400 shadow-[0_4px_20px_rgba(34,211,238,0.3)]">
          <span className="text-xl">⚡</span>
        </div>
        <div>
          <span className="text-lg font-bold text-slate-100">Continuum</span>
          <div className="text-[11px] text-slate-500 capitalize">Knowledge Graph</div>
        </div>
      </div>

      <Separator className="bg-white/[0.06]" />

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-gradient-to-r from-cyan-500/20 to-teal-500/10 border border-cyan-500/40 text-cyan-400"
                  : "text-slate-400 hover:bg-white/[0.03] hover:text-slate-200 border border-transparent"
              )}
            >
              <span className="text-lg">{item.icon}</span>
              {item.name}
            </Link>
          )
        })}
      </nav>

      <Separator className="bg-white/[0.06]" />

      {/* User section */}
      <div className="p-4">
        <div className="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-3 border border-white/[0.06]">
          <Avatar className="h-10 w-10 bg-gradient-to-br from-cyan-500 to-teal-400">
            <AvatarFallback className="bg-transparent text-slate-900 font-semibold">
              {session?.user?.name?.charAt(0).toUpperCase() || "U"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 truncate">
            <p className="text-sm font-medium text-slate-200">
              {session?.user?.name || "User"}
            </p>
            <p className="text-xs text-slate-500 truncate">
              {session?.user?.email || ""}
            </p>
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex-1 text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
          >
            ⚙️
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => signOut()}
            className="flex-1 text-slate-400 hover:text-slate-200 hover:bg-white/[0.05]"
          >
            🚪
          </Button>
        </div>
      </div>
    </div>
  )
}
