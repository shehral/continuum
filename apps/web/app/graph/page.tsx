"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"

import { AppShell } from "@/components/layout/app-shell"
import { KnowledgeGraph } from "@/components/graph/knowledge-graph"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { RefreshCw } from "lucide-react"

export default function GraphPage() {
  const [sourceFilter, setSourceFilter] = useState<string | null>(null)

  const {
    data: graphData,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["graph", sourceFilter],
    queryFn: () =>
      api.getGraph({
        include_similarity: true,
        include_temporal: true,
        include_entity_relations: true,
        source_filter: sourceFilter as "claude_logs" | "interview" | "manual" | "unknown" | undefined,
      }),
  })

  const { data: sourceCounts } = useQuery({
    queryKey: ["graph-sources"],
    queryFn: () => api.getDecisionSources(),
  })

  const handleSourceFilterChange = (source: string | null) => {
    setSourceFilter(source)
  }

  return (
    <AppShell>
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-slate-900/80 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Knowledge Graph</h1>
            <p className="text-sm text-slate-400">
              Explore decisions and their relationships
              {sourceFilter && (
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                  Filtered: {sourceFilter === "claude_logs" ? "AI Extracted" :
                            sourceFilter === "interview" ? "Human Captured" :
                            sourceFilter === "manual" ? "Manual Entry" : "Legacy"}
                </span>
              )}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100 hover:scale-105 transition-all"
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>

        {/* Graph */}
        <div className="flex-1">
          {isLoading ? (
            <div className="h-full flex items-center justify-center bg-slate-900/50">
              <div className="text-center animate-in fade-in zoom-in duration-500">
                <div className="relative mx-auto mb-4 h-16 w-16">
                  <div className="absolute inset-0 rounded-full bg-cyan-500/20 animate-ping" />
                  <div className="relative h-full w-full rounded-full bg-cyan-500/10 flex items-center justify-center">
                    <RefreshCw className="h-8 w-8 animate-spin text-cyan-400" />
                  </div>
                </div>
                <p className="text-slate-400">Loading knowledge graph...</p>
              </div>
            </div>
          ) : (
            <KnowledgeGraph
              data={graphData}
              sourceFilter={sourceFilter}
              onSourceFilterChange={handleSourceFilterChange}
              sourceCounts={sourceCounts || {}}
            />
          )}
        </div>
      </div>
    </AppShell>
  )
}
