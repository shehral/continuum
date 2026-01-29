"use client"

import { useCallback, useMemo, useState } from "react"
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  Panel,
  NodeProps,
  Handle,
  Position,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { X, Sparkles, GitBranch, ArrowRight, Link2, Bot, User, FileText } from "lucide-react"
import { type GraphData, type Decision, type Entity } from "@/lib/api"

// Decision source configuration
const SOURCE_STYLES: Record<string, {
  color: string
  borderColor: string
  icon: React.ReactNode
  label: string
  description: string
}> = {
  claude_logs: {
    color: "from-purple-800/90 to-purple-900/90",
    borderColor: "border-purple-500/50",
    icon: <Bot className="h-4 w-4 text-purple-400" />,
    label: "AI Extracted",
    description: "Extracted from Claude Code logs",
  },
  interview: {
    color: "from-emerald-800/90 to-emerald-900/90",
    borderColor: "border-emerald-500/50",
    icon: <User className="h-4 w-4 text-emerald-400" />,
    label: "Human Captured",
    description: "Captured via AI-guided interview",
  },
  manual: {
    color: "from-amber-800/90 to-amber-900/90",
    borderColor: "border-amber-500/50",
    icon: <FileText className="h-4 w-4 text-amber-400" />,
    label: "Manual Entry",
    description: "Manually entered by user",
  },
  unknown: {
    color: "from-slate-800/90 to-slate-900/90",
    borderColor: "border-cyan-500/30",
    icon: <Sparkles className="h-4 w-4 text-cyan-400" />,
    label: "Legacy",
    description: "Created before source tracking",
  },
}

// Relationship type styling configuration
const RELATIONSHIP_STYLES: Record<string, {
  color: string
  label: string
  icon: string
  strokeDasharray?: string
  animated?: boolean
}> = {
  INVOLVES: {
    color: "#22D3EE",
    label: "Involves",
    icon: "🔗",
    strokeDasharray: "5,5",
    animated: true,
  },
  SIMILAR_TO: {
    color: "#A78BFA",
    label: "Similar To",
    icon: "✨",
    animated: true,
  },
  INFLUENCED_BY: {
    color: "#F59E0B",
    label: "Influenced By",
    icon: "⏳",
    strokeDasharray: "10,5",
  },
  IS_A: {
    color: "#10B981",
    label: "Is A",
    icon: "↗️",
  },
  PART_OF: {
    color: "#3B82F6",
    label: "Part Of",
    icon: "📦",
  },
  RELATED_TO: {
    color: "#EC4899",
    label: "Related To",
    icon: "🔄",
    strokeDasharray: "3,3",
  },
  DEPENDS_ON: {
    color: "#EF4444",
    label: "Depends On",
    icon: "⚡",
  },
}

// Custom node component for decisions
function DecisionNode({ data, selected }: NodeProps) {
  const nodeData = data as { label: string; decision?: Decision & { source?: string }; hasEmbedding?: boolean }
  const source = nodeData.decision?.source || "unknown"
  const sourceStyle = SOURCE_STYLES[source] || SOURCE_STYLES.unknown

  return (
    <div
      className={`
        px-5 py-4 rounded-2xl min-w-[220px] max-w-[320px]
        bg-gradient-to-br ${sourceStyle.color}
        backdrop-blur-xl
        border-2 transition-all duration-200
        ${selected
          ? "border-white shadow-[0_0_30px_rgba(255,255,255,0.2)]"
          : `${sourceStyle.borderColor} hover:border-white/50 shadow-[0_4px_20px_rgba(0,0,0,0.3)]`
        }
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-white/80 !border-2 !border-slate-800"
      />
      <div className="flex items-center gap-2 mb-2">
        {sourceStyle.icon}
        <Badge
          className="text-[10px]"
          style={{
            backgroundColor: source === "claude_logs" ? "rgba(168,85,247,0.2)" :
                            source === "interview" ? "rgba(16,185,129,0.2)" :
                            source === "manual" ? "rgba(245,158,11,0.2)" :
                            "rgba(34,211,238,0.2)",
            color: source === "claude_logs" ? "#c084fc" :
                   source === "interview" ? "#34d399" :
                   source === "manual" ? "#fbbf24" :
                   "#22d3ee",
            borderColor: source === "claude_logs" ? "rgba(168,85,247,0.3)" :
                         source === "interview" ? "rgba(16,185,129,0.3)" :
                         source === "manual" ? "rgba(245,158,11,0.3)" :
                         "rgba(34,211,238,0.3)",
          }}
        >
          {sourceStyle.label}
        </Badge>
        {nodeData.hasEmbedding && (
          <span title="Has semantic embedding">
            <Sparkles className="h-3 w-3 text-purple-400" />
          </span>
        )}
      </div>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="font-semibold text-sm text-slate-100 line-clamp-2 cursor-help">
              {nodeData.label}
            </div>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-sm">
            <p>{nodeData.label}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="text-xs text-slate-400 mt-2 line-clamp-2 cursor-help">
              {nodeData.decision?.decision || "Decision trace"}
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-sm">
            <p>{nodeData.decision?.decision || "Decision trace"}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-white/80 !border-2 !border-slate-800"
      />
    </div>
  )
}

// Custom node component for entities
function EntityNode({ data, selected }: NodeProps) {
  const nodeData = data as { label: string; entity?: Entity; hasEmbedding?: boolean }

  const typeConfig: Record<string, { color: string; icon: string; bg: string }> = {
    concept: {
      color: "border-blue-400",
      icon: "🔮",
      bg: "from-blue-500/20 to-blue-600/10",
    },
    system: {
      color: "border-green-400",
      icon: "⚙️",
      bg: "from-green-500/20 to-green-600/10",
    },
    person: {
      color: "border-purple-400",
      icon: "👤",
      bg: "from-purple-500/20 to-purple-600/10",
    },
    technology: {
      color: "border-orange-400",
      icon: "🔧",
      bg: "from-orange-500/20 to-orange-600/10",
    },
    pattern: {
      color: "border-pink-400",
      icon: "🎯",
      bg: "from-pink-500/20 to-pink-600/10",
    },
  }

  const config = typeConfig[nodeData.entity?.type || "concept"] || typeConfig.concept
  const selectedClass = selected
    ? `shadow-[0_0_25px_rgba(59,130,246,0.4)] scale-105`
    : "hover:scale-105"

  return (
    <div
      className={`
        px-4 py-3 rounded-full
        bg-gradient-to-br ${config.bg}
        backdrop-blur-xl
        border-2 ${config.color}
        transition-all duration-200
        ${selectedClass}
      `}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-slate-400 !border-slate-700"
      />
      <div className="flex items-center gap-2">
        <span className="text-base">{config.icon}</span>
        <span className="font-medium text-sm text-slate-200 whitespace-nowrap">
          {nodeData.label}
        </span>
        {nodeData.hasEmbedding && (
          <span title="Has semantic embedding">
            <Sparkles className="h-3 w-3 text-purple-400" />
          </span>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !bg-slate-400 !border-slate-700"
      />
    </div>
  )
}

const nodeTypes = {
  decision: DecisionNode,
  entity: EntityNode,
}

interface KnowledgeGraphProps {
  data?: GraphData
  onNodeClick?: (node: Node) => void
  sourceFilter?: string | null
  onSourceFilterChange?: (source: string | null) => void
  sourceCounts?: Record<string, number>
}

export function KnowledgeGraph({
  data,
  onNodeClick,
  sourceFilter,
  onSourceFilterChange,
  sourceCounts = {},
}: KnowledgeGraphProps) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [showRelationshipLegend, setShowRelationshipLegend] = useState(true)
  const [showSourceLegend, setShowSourceLegend] = useState(true)

  // Convert graph data to React Flow format with better layout
  const initialNodes: Node[] = useMemo(() => {
    if (!data?.nodes) return []

    const decisionNodes = data.nodes.filter((n) => n.type === "decision")
    const entityNodes = data.nodes.filter((n) => n.type === "entity")

    const nodes: Node[] = []

    // Layout decisions in a row at the top
    decisionNodes.forEach((node, index) => {
      nodes.push({
        id: node.id,
        type: node.type,
        position: {
          x: index * 400 + 100,
          y: 50,
        },
        data: {
          label: node.label,
          decision: node.data,
          hasEmbedding: node.has_embedding,
        },
      })
    })

    // Layout entities in a grid below
    entityNodes.forEach((node, index) => {
      const cols = Math.ceil(Math.sqrt(entityNodes.length))
      const row = Math.floor(index / cols)
      const col = index % cols
      nodes.push({
        id: node.id,
        type: node.type,
        position: {
          x: col * 200 + 150,
          y: row * 120 + 300,
        },
        data: {
          label: node.label,
          entity: node.data,
          hasEmbedding: node.has_embedding,
        },
      })
    })

    return nodes
  }, [data])

  const initialEdges: Edge[] = useMemo(() => {
    if (!data?.edges) return []

    return data.edges.map((edge) => {
      const relStyle = RELATIONSHIP_STYLES[edge.relationship] || RELATIONSHIP_STYLES.INVOLVES
      const weight = edge.weight ?? 1.0

      // Calculate stroke width based on weight (similarity score)
      const strokeWidth = Math.max(1.5, Math.min(4, weight * 3))

      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: weight < 1.0 ? `${relStyle.label} (${(weight * 100).toFixed(0)}%)` : relStyle.label,
        animated: relStyle.animated ?? false,
        labelStyle: {
          fill: relStyle.color,
          fontSize: 10,
          fontWeight: 500,
        },
        labelBgStyle: {
          fill: "rgba(15, 23, 42, 0.9)",
          fillOpacity: 0.9,
        },
        labelBgPadding: [6, 4] as [number, number],
        labelBgBorderRadius: 6,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: relStyle.color,
          width: 15,
          height: 15,
        },
        style: {
          stroke: relStyle.color,
          strokeWidth,
          strokeDasharray: relStyle.strokeDasharray,
          opacity: 0.8 + (weight * 0.2),
        },
      }
    })
  }, [data])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  // Count relationships by type
  const relationshipCounts = useMemo(() => {
    if (!data?.edges) return {}
    return data.edges.reduce((acc, edge) => {
      acc[edge.relationship] = (acc[edge.relationship] || 0) + 1
      return acc
    }, {} as Record<string, number>)
  }, [data])

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node)
      onNodeClick?.(node)
    },
    [onNodeClick]
  )

  const closeDetailPanel = () => setSelectedNode(null)

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 1.5 }}
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.5 }}
        className="!bg-transparent"
        proOptions={{ hideAttribution: true }}
      >
        <Controls
          className="!bg-slate-800/80 !border-white/10 !rounded-xl [&>button]:!bg-slate-700/50 [&>button]:!border-white/10 [&>button]:!text-slate-300 [&>button:hover]:!bg-slate-600/50"
        />
        <MiniMap
          nodeColor={(node) =>
            node.type === "decision" ? "#22D3EE" : "#64748B"
          }
          maskColor="rgba(15, 23, 42, 0.8)"
          className="!bg-slate-800/80 !border-white/10 !rounded-xl"
        />
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="rgba(148, 163, 184, 0.15)"
        />

        {/* Source Filter Panel */}
        {showSourceLegend && (
          <Panel position="top-left" className="m-4">
            <Card className="w-56 bg-slate-800/90 backdrop-blur-xl border-white/10">
              <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                <CardTitle className="text-sm text-slate-200 flex items-center gap-2">
                  <Bot className="h-4 w-4" /> Decision Sources
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowSourceLegend(false)}
                  className="h-6 w-6 text-slate-400 hover:text-slate-200"
                  aria-label="Close source legend"
                >
                  <X className="h-3 w-3" />
                </Button>
              </CardHeader>
              <CardContent className="py-2 px-4 space-y-1.5">
                {/* All sources button */}
                <button
                  onClick={() => onSourceFilterChange?.(null)}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                    !sourceFilter
                      ? "bg-white/10 border border-white/20"
                      : "hover:bg-white/5"
                  }`}
                >
                  <div className="w-4 h-4 rounded bg-gradient-to-br from-slate-600 to-slate-700 border border-white/20" />
                  <span className="text-xs text-slate-300 flex-1 text-left">All Sources</span>
                  <Badge className="text-[9px] px-1.5 py-0 bg-slate-700 text-slate-300 border-slate-600">
                    {Object.values(sourceCounts).reduce((a, b) => a + b, 0)}
                  </Badge>
                </button>

                {/* Individual source filters */}
                {Object.entries(SOURCE_STYLES).map(([key, style]) => {
                  const count = sourceCounts[key] || 0
                  if (count === 0 && key !== "unknown") return null
                  return (
                    <button
                      key={key}
                      onClick={() => onSourceFilterChange?.(sourceFilter === key ? null : key)}
                      className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                        sourceFilter === key
                          ? "bg-white/10 border border-white/20"
                          : "hover:bg-white/5"
                      }`}
                    >
                      {style.icon}
                      <span className="text-xs text-slate-300 flex-1 text-left">{style.label}</span>
                      <Badge
                        className="text-[9px] px-1.5 py-0"
                        style={{
                          backgroundColor: key === "claude_logs" ? "rgba(168,85,247,0.2)" :
                                          key === "interview" ? "rgba(16,185,129,0.2)" :
                                          key === "manual" ? "rgba(245,158,11,0.2)" :
                                          "rgba(100,116,139,0.2)",
                          color: key === "claude_logs" ? "#c084fc" :
                                 key === "interview" ? "#34d399" :
                                 key === "manual" ? "#fbbf24" :
                                 "#94a3b8",
                          borderColor: "transparent",
                        }}
                      >
                        {count}
                      </Badge>
                    </button>
                  )
                })}

                <div className="pt-2 mt-2 border-t border-white/10">
                  <p className="text-[10px] text-slate-500">
                    {sourceFilter
                      ? `Showing ${sourceCounts[sourceFilter] || 0} ${SOURCE_STYLES[sourceFilter]?.label || sourceFilter} decisions`
                      : "Click to filter by source"}
                  </p>
                </div>
              </CardContent>
            </Card>
          </Panel>
        )}

        {/* Node Type Legend */}
        <Panel position="top-left" className="m-4" style={{ marginTop: showSourceLegend ? '280px' : '0' }}>
          <Card className="w-52 bg-slate-800/90 backdrop-blur-xl border-white/10" role="region" aria-label="Entity types legend">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm text-slate-200 flex items-center gap-2">
                <span role="img" aria-label="Chart icon">📊</span> Entity Types
              </CardTitle>
            </CardHeader>
            <CardContent className="py-2 px-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-blue-500/20 border-2 border-blue-400" />
                <span className="text-xs text-slate-300">🔮 Concept</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-green-500/20 border-2 border-green-400" />
                <span className="text-xs text-slate-300">⚙️ System</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-orange-500/20 border-2 border-orange-400" />
                <span className="text-xs text-slate-300">🔧 Technology</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-purple-500/20 border-2 border-purple-400" />
                <span className="text-xs text-slate-300">👤 Person</span>
              </div>
              <div className="flex items-center gap-2 pt-1 border-t border-white/10 mt-2">
                <Sparkles className="h-4 w-4 text-purple-400" />
                <span className="text-xs text-slate-400">= Has embedding</span>
              </div>
            </CardContent>
          </Card>
        </Panel>

        {/* Relationship Legend */}
        {showRelationshipLegend && (
          <Panel position="top-right" className="m-4">
            <Card className="w-56 bg-slate-800/90 backdrop-blur-xl border-white/10" role="region" aria-label="Relationship types legend">
              <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                <CardTitle className="text-sm text-slate-200 flex items-center gap-2">
                  <GitBranch className="h-4 w-4" /> Relationships
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowRelationshipLegend(false)}
                  className="h-6 w-6 text-slate-400 hover:text-slate-200"
                  aria-label="Close relationship legend"
                >
                  <X className="h-3 w-3" />
                </Button>
              </CardHeader>
              <CardContent className="py-2 px-4 space-y-1.5">
                {Object.entries(RELATIONSHIP_STYLES).map(([key, style]) => {
                  const count = relationshipCounts[key] || 0
                  if (count === 0 && key !== "INVOLVES") return null
                  return (
                    <div key={key} className="flex items-center gap-2">
                      <div
                        className="w-6 h-0.5 rounded"
                        style={{
                          backgroundColor: style.color,
                          opacity: count > 0 ? 1 : 0.3,
                        }}
                      />
                      <span className="text-xs text-slate-300 flex-1">
                        {style.icon} {style.label}
                      </span>
                      {count > 0 && (
                        <Badge
                          className="text-[9px] px-1.5 py-0"
                          style={{
                            backgroundColor: `${style.color}20`,
                            color: style.color,
                            borderColor: `${style.color}40`,
                          }}
                        >
                          {count}
                        </Badge>
                      )}
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          </Panel>
        )}

        {/* Tip Panel */}
        <Panel position="bottom-left" className="m-4">
          <div className="px-3 py-2 rounded-lg bg-slate-800/80 backdrop-blur-xl border border-white/10 text-xs text-slate-400">
            💡 Click and drag to pan • Scroll to zoom • Click nodes for details
          </div>
        </Panel>

        {/* Stats Panel */}
        <Panel position="bottom-right" className="m-4">
          <div className="px-3 py-2 rounded-lg bg-slate-800/80 backdrop-blur-xl border border-white/10 text-xs text-slate-400 flex gap-4">
            <span>📍 {data?.nodes?.length || 0} nodes</span>
            <span>🔗 {data?.edges?.length || 0} edges</span>
          </div>
        </Panel>
      </ReactFlow>

      {/* Detail Panel */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-80 z-10" style={{ marginTop: showRelationshipLegend ? '220px' : '0' }}>
          <Card className="bg-slate-800/95 backdrop-blur-xl border-white/10 shadow-2xl">
            <CardHeader className="flex flex-row items-center justify-between py-3 border-b border-white/10">
              <CardTitle className="text-base text-slate-100 flex items-center gap-2">
                {selectedNode.type === "decision" ? "💡" : "🔮"}
                {selectedNode.type === "decision" ? "Decision" : "Entity"} Details
              </CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={closeDetailPanel}
                className="h-8 w-8 text-slate-400 hover:text-slate-200 hover:bg-white/10"
              >
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="pt-4">
              <ScrollArea className="h-[320px] pr-2">
                {selectedNode.type === "decision" && (() => {
                  const decisionData = selectedNode.data as { decision?: Decision; hasEmbedding?: boolean }
                  if (!decisionData.decision) return null
                  const decision = decisionData.decision
                  return (
                    <div className="space-y-4">
                      {decisionData.hasEmbedding && (
                        <div className="flex items-center gap-2 text-xs text-purple-400 bg-purple-500/10 rounded-lg px-3 py-2">
                          <Sparkles className="h-3 w-3" />
                          <span>Semantic search enabled</span>
                        </div>
                      )}
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">
                          Trigger
                        </h4>
                        <p className="text-sm text-slate-200">{decision.trigger}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">
                          Context
                        </h4>
                        <p className="text-sm text-slate-300">{decision.context}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">
                          Decision
                        </h4>
                        <p className="text-sm text-slate-200 font-medium">{decision.decision}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">
                          Rationale
                        </h4>
                        <p className="text-sm text-slate-300">{decision.rationale}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-2">
                          Related Entities
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {(decision.entities ?? []).length > 0 ? (
                            decision.entities.map((entity) => (
                              <Badge
                                key={entity.id}
                                className="bg-blue-500/20 text-blue-400 border-blue-500/30"
                              >
                                ⚙️ {entity.name}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-sm text-slate-500">No entities linked</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })()}
                {selectedNode.type === "entity" && (() => {
                  const entityData = selectedNode.data as { entity?: Entity; hasEmbedding?: boolean }
                  if (!entityData.entity) return null
                  const entity = entityData.entity
                  return (
                    <div className="space-y-4">
                      {entityData.hasEmbedding && (
                        <div className="flex items-center gap-2 text-xs text-purple-400 bg-purple-500/10 rounded-lg px-3 py-2">
                          <Sparkles className="h-3 w-3" />
                          <span>Semantic search enabled</span>
                        </div>
                      )}
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">
                          Name
                        </h4>
                        <p className="text-lg font-semibold text-slate-100">{entity.name}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">
                          Type
                        </h4>
                        <Badge className="bg-slate-700 text-slate-200 border-slate-600 capitalize">
                          {entity.type}
                        </Badge>
                      </div>
                    </div>
                  )
                })()}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
