"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api, type DashboardStats, type Decision } from "@/lib/api"

function StatCard({
  title,
  value,
  description,
  icon,
}: {
  title: string
  value: number | string
  description: string
  icon: string
}) {
  return (
    <Card className="bg-white/[0.03] backdrop-blur-xl border-white/[0.06]">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <CardTitle className="text-sm font-medium text-slate-400">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-teal-400 bg-clip-text text-transparent">
          {value}
        </div>
        <p className="text-xs text-slate-500 mt-1">{description}</p>
      </CardContent>
    </Card>
  )
}

function DecisionCard({ decision }: { decision: Decision }) {
  return (
    <Card className="bg-white/[0.03] backdrop-blur-xl border-white/[0.06] hover:bg-white/[0.05] transition-all duration-200">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-base line-clamp-1 text-slate-200">
            {decision.trigger}
          </CardTitle>
          <Badge className="ml-2 shrink-0 bg-cyan-500/20 text-cyan-400 border-cyan-500/30">
            {Math.round(decision.confidence * 100)}%
          </Badge>
        </div>
        <CardDescription className="line-clamp-2 text-slate-400">
          {decision.decision}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-1">
          {decision.entities.slice(0, 3).map((entity) => (
            <Badge
              key={entity.id}
              variant="outline"
              className="text-xs bg-blue-500/10 text-blue-400 border-blue-500/30"
            >
              ⚙️ {entity.name}
            </Badge>
          ))}
          {decision.entities.length > 3 && (
            <Badge variant="outline" className="text-xs text-slate-400 border-slate-600">
              +{decision.entities.length - 3} more
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.getDashboardStats(),
  })

  // Fallback data for when API is not available
  const displayStats: DashboardStats = stats || {
    total_decisions: 0,
    total_entities: 0,
    total_sessions: 0,
    recent_decisions: [],
  }

  return (
    <AppShell>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-100">
              Welcome back! 👋
            </h1>
            <p className="text-slate-400">
              Your knowledge graph at a glance
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              asChild
              className="bg-white/[0.05] border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100"
            >
              <Link href="/graph">🔗 View Graph</Link>
            </Button>
            <Button
              asChild
              className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)] hover:shadow-[0_6px_20px_rgba(34,211,238,0.4)]"
            >
              <Link href="/add">🧠 Add Knowledge</Link>
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Decisions"
            value={displayStats.total_decisions}
            description="Decision traces captured"
            icon="📝"
          />
          <StatCard
            title="Entities"
            value={displayStats.total_entities}
            description="Concepts, systems, patterns"
            icon="🔗"
          />
          <StatCard
            title="Capture Sessions"
            value={displayStats.total_sessions}
            description="Interview sessions completed"
            icon="💬"
          />
          <StatCard
            title="Graph Connections"
            value={displayStats.total_entities * 2}
            description="Relationships mapped"
            icon="📊"
          />
        </div>

        {/* Recent Decisions */}
        <Card className="bg-white/[0.03] backdrop-blur-xl border-white/[0.06]">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl text-slate-100">Recent Decisions</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                asChild
                className="text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10"
              >
                <Link href="/decisions">View all →</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {displayStats.recent_decisions.length === 0 ? (
              <div className="py-8 text-center">
                <div className="mx-auto mb-4 h-16 w-16 rounded-2xl bg-white/[0.05] flex items-center justify-center">
                  <span className="text-3xl">📋</span>
                </div>
                <h3 className="text-lg font-medium mb-1 text-slate-200">No decisions yet</h3>
                <p className="text-slate-400 mb-4 max-w-md mx-auto">
                  Start capturing knowledge from your Claude Code sessions or through guided interviews.
                </p>
                <Button
                  asChild
                  className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)]"
                >
                  <Link href="/add">🧠 Add Knowledge</Link>
                </Button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {displayStats.recent_decisions.map((decision) => (
                  <DecisionCard key={decision.id} decision={decision} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
