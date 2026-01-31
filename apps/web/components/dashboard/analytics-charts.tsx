"use client"

import { useMemo } from "react"
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, PieChart as PieChartIcon, BarChart3, Activity } from "lucide-react"

interface Decision {
  id: string
  created_at: string
  confidence: number
  entities: Array<{ type: string }>
}

interface AnalyticsChartsProps {
  decisions: Decision[]
}

const ENTITY_TYPE_COLORS: Record<string, string> = {
  technology: "#3b82f6",
  pattern: "#8b5cf6",
  concept: "#10b981",
  person: "#f59e0b",
  team: "#ec4899",
  component: "#06b6d4",
  other: "#6b7280",
}

const CONFIDENCE_COLORS = ["#fee2e2", "#fecaca", "#fca5a5", "#f87171", "#ef4444"]

export function AnalyticsCharts({ decisions }: AnalyticsChartsProps) {
  const decisionsOverTime = useMemo(() => {
    const now = new Date()
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    const dateCounts: Record<string, number> = {}

    for (let d = new Date(thirtyDaysAgo); d <= now; d.setDate(d.getDate() + 1)) {
      const dateStr = d.toISOString().split("T")[0]
      dateCounts[dateStr] = 0
    }

    decisions.forEach((decision) => {
      const dateStr = decision.created_at.split("T")[0]
      if (dateCounts[dateStr] !== undefined) {
        dateCounts[dateStr]++
      }
    })

    return Object.entries(dateCounts)
      .map(([date, count]) => ({
        date: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        fullDate: date,
        count,
      }))
      .slice(-14)
  }, [decisions])

  const entityTypeDistribution = useMemo(() => {
    const typeCounts: Record<string, number> = {}

    decisions.forEach((decision) => {
      decision.entities?.forEach((entity) => {
        const type = entity.type || "other"
        typeCounts[type] = (typeCounts[type] || 0) + 1
      })
    })

    return Object.entries(typeCounts)
      .map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
        color: ENTITY_TYPE_COLORS[name] || ENTITY_TYPE_COLORS.other,
      }))
      .sort((a, b) => b.value - a.value)
  }, [decisions])

  const confidenceDistribution = useMemo(() => {
    const buckets = [
      { range: "0-20%", min: 0, max: 0.2, count: 0 },
      { range: "20-40%", min: 0.2, max: 0.4, count: 0 },
      { range: "40-60%", min: 0.4, max: 0.6, count: 0 },
      { range: "60-80%", min: 0.6, max: 0.8, count: 0 },
      { range: "80-100%", min: 0.8, max: 1.0, count: 0 },
    ]

    decisions.forEach((decision) => {
      const conf = decision.confidence || 0
      const bucket = buckets.find((b) => conf >= b.min && conf < b.max) || buckets[buckets.length - 1]
      bucket.count++
    })

    return buckets
  }, [decisions])

  const quickStats = useMemo(() => {
    const avgConfidence = decisions.length > 0
      ? decisions.reduce((sum, d) => sum + (d.confidence || 0), 0) / decisions.length
      : 0

    const totalEntities = decisions.reduce((sum, d) => sum + (d.entities?.length || 0), 0)

    const recentCount = decisions.filter((d) => {
      const created = new Date(d.created_at)
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      return created >= weekAgo
    }).length

    return {
      avgConfidence: Math.round(avgConfidence * 100),
      totalEntities,
      recentCount,
      avgEntitiesPerDecision: decisions.length > 0 ? (totalEntities / decisions.length).toFixed(1) : "0",
    }
  }, [decisions])

  if (decisions.length === 0) {
    return (
      <Card className="col-span-full">
        <CardContent className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">No decisions yet to analyze</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Decisions Over Time</CardTitle>
          </div>
          <CardDescription>Last 14 days</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={decisionsOverTime}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" fontSize={11} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <PieChartIcon className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Entity Types</CardTitle>
          </div>
          <CardDescription>Distribution of extracted entities</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            {entityTypeDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={entityTypeDistribution} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={2} dataKey="value">
                    {entityTypeDistribution.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="middle" align="right" layout="vertical" iconType="circle" iconSize={8} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-muted-foreground">No entities extracted yet</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Confidence Distribution</CardTitle>
          </div>
          <CardDescription>Extraction confidence levels</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={confidenceDistribution}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="range" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {confidenceDistribution.map((_, index) => (
                    <Cell key={index} fill={CONFIDENCE_COLORS[index]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Quick Stats</CardTitle>
          </div>
          <CardDescription>Summary metrics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-2xl font-bold">{quickStats.avgConfidence}%</p>
              <p className="text-xs text-muted-foreground">Avg Confidence</p>
            </div>
            <div className="space-y-1">
              <p className="text-2xl font-bold">{quickStats.totalEntities}</p>
              <p className="text-xs text-muted-foreground">Total Entities</p>
            </div>
            <div className="space-y-1">
              <p className="text-2xl font-bold">{quickStats.recentCount}</p>
              <p className="text-xs text-muted-foreground">This Week</p>
            </div>
            <div className="space-y-1">
              <p className="text-2xl font-bold">{quickStats.avgEntitiesPerDecision}</p>
              <p className="text-xs text-muted-foreground">Entities/Decision</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
