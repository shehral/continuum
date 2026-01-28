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
        <div className="flex items-center justify-between px-6 py-4 border-b bg-background">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Knowledge Graph</h1>
            <p className="text-sm text-muted-foreground">
              Explore decisions and their relationships
              {sourceFilter && (
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-muted">
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
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">Loading graph...</p>
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
