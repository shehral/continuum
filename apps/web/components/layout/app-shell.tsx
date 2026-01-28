"use client"

import { Sidebar } from "./sidebar"

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Ambient background effects */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: `
            radial-gradient(ellipse at 20% 20%, rgba(34, 211, 238, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 80%, rgba(20, 184, 166, 0.05) 0%, transparent 50%)
          `
        }}
      />

      <Sidebar />
      <main className="flex-1 overflow-auto relative z-10">
        {children}
      </main>
    </div>
  )
}
