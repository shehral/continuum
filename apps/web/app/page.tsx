"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { useEffect, useState } from "react"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api, type DashboardStats, type Decision } from "@/lib/api"
import { entityStyles, getEntityStyle } from "@/lib/constants"

// Animated number counter for stats
function AnimatedNumber({ value, duration = 1000 }: { value: number; duration?: number }) {
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    if (value === 0) {
      setDisplayValue(0)
      return
    }

    const startTime = Date.now()
    const startValue = 0

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3)
      setDisplayValue(Math.floor(startValue + (value - startValue) * easeOut))

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [value, duration])

  return <>{displayValue}</>
}

function StatCard({
  title,
  value,
  description,
  icon,
  href,
  emptyAction,
  delay = 0,
}: {
  title: string
  value: number | string
  description: string
  icon: string
  href?: string
  emptyAction?: { label: string; href: string }
  delay?: number
}) {
  const isEmpty = value === 0 || value === "0"
  const numericValue = typeof value === "number" ? value : parseInt(value) || 0

  const content = (
    <Card
      className={`bg-white/[0.03] backdrop-blur-xl border-white/[0.06] transition-all duration-300 animate-in fade-in slide-in-from-bottom-4 ${href ? 'hover:bg-white/[0.06] hover:border-cyan-500/20 hover:scale-[1.02] cursor-pointer' : ''}`}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'backwards' }}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <CardTitle className="text-sm font-medium text-slate-400">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className={`text-4xl font-bold bg-gradient-to-r ${isEmpty ? 'from-slate-500 to-slate-400' : 'from-cyan-400 to-teal-400'} bg-clip-text text-transparent`}>
          {typeof value === "number" ? <AnimatedNumber value={numericValue} /> : value}
        </div>
        <p className="text-xs text-slate-500 mt-1">{description}</p>
        {isEmpty && emptyAction && (
          <Link
            href={emptyAction.href}
            className="text-xs text-cyan-400 hover:text-cyan-300 mt-2 inline-flex items-center gap-1 transition-colors group"
          >
            {emptyAction.label}
            <span className="group-hover:translate-x-1 transition-transform">→</span>
          </Link>
        )}
      </CardContent>
    </Card>
  )

  return href && !isEmpty ? <Link href={href}>{content}</Link> : content
}

function DecisionCard({ decision, index = 0 }: { decision: Decision; index?: number }) {
  return (
    <Link href={`/decisions?id=${decision.id}`}>
      <Card
        className="h-full bg-white/[0.03] backdrop-blur-xl border-white/[0.06] hover:bg-white/[0.06] hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] hover:scale-[1.02] transition-all duration-300 cursor-pointer group animate-in fade-in slide-in-from-bottom-4"
        style={{ animationDelay: `${400 + index * 100}ms`, animationFillMode: 'backwards' }}
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base text-slate-200 group-hover:text-cyan-300 transition-colors leading-tight">
              {decision.trigger}
            </CardTitle>
            <Badge className="ml-2 shrink-0 bg-cyan-500/20 text-cyan-400 border-cyan-500/30 group-hover:bg-cyan-500/30 transition-colors">
              {Math.round(decision.confidence * 100)}%
            </Badge>
          </div>
          <CardDescription className="line-clamp-2 text-slate-400 mt-1">
            {decision.decision}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1.5">
            {decision.entities.slice(0, 3).map((entity) => {
              const style = getEntityStyle(entity.type)
              return (
                <Badge
                  key={entity.id}
                  variant="outline"
                  className={`text-xs ${style.bg} ${style.text} ${style.border} transition-all hover:scale-105`}
                >
                  {style.icon} {entity.name}
                </Badge>
              )
            })}
            {decision.entities.length > 3 && (
              <Badge variant="outline" className="text-xs text-slate-400 border-slate-600 bg-slate-500/10">
                +{decision.entities.length - 3} more
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
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
        <div className="flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-500">
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
              className="bg-white/[0.05] border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100 hover:scale-105 transition-all"
            >
              <Link href="/graph">🔗 View Graph</Link>
            </Button>
            <Button
              asChild
              className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)] hover:shadow-[0_6px_20px_rgba(34,211,238,0.4)] hover:scale-105 transition-all"
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
            href="/decisions"
            emptyAction={{ label: "Import from Claude logs", href: "/add" }}
            delay={0}
          />
          <StatCard
            title="Entities"
            value={displayStats.total_entities}
            description="Concepts, systems, patterns"
            icon="🔗"
            href="/graph"
            emptyAction={{ label: "Add knowledge", href: "/add" }}
            delay={100}
          />
          <StatCard
            title="Capture Sessions"
            value={displayStats.total_sessions}
            description="AI-guided interviews"
            icon="💬"
            href="/capture"
            emptyAction={{ label: "Start an interview", href: "/capture" }}
            delay={200}
          />
          <StatCard
            title="Graph Connections"
            value={displayStats.total_entities * 2}
            description="Relationships mapped"
            icon="📊"
            href="/graph"
            delay={300}
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
                {displayStats.recent_decisions.map((decision, index) => (
                  <DecisionCard key={decision.id} decision={decision} index={index} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
