"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
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
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { X, Sparkles, GitBranch, Bot, User, FileText, Trash2 } from "lucide-react"
import { type GraphData, type Decision, type Entity } from "@/lib/api"
import { DeleteConfirmDialog } from "@/components/ui/confirm-dialog"

// Pre-computed style objects for source badges (P1-3)
const SOURCE_BADGE_STYLES = {
  claude_logs: {
    backgroundColor: "rgba(168,85,247,0.2)",
    color: "#c084fc",
    borderColor: "rgba(168,85,247,0.3)",
  },
  interview: {
    backgroundColor: "rgba(16,185,129,0.2)",
    color: "#34d399",
    borderColor: "rgba(16,185,129,0.3)",
  },
  manual: {
    backgroundColor: "rgba(245,158,11,0.2)",
    color: "#fbbf24",
    borderColor: "rgba(245,158,11,0.3)",
  },
  unknown: {
    backgroundColor: "rgba(34,211,238,0.2)",
    color: "#22d3ee",
    borderColor: "rgba(34,211,238,0.3)",
  },
} as const

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

// Relationship type styling configuration with accessibility patterns (P2-4)
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
    icon: "links",
    strokeDasharray: "5,5",
    animated: true,
  },
  SIMILAR_TO: {
    color: "#A78BFA",
    label: "Similar To",
    icon: "sparkles",
    animated: true,
  },
  INFLUENCED_BY: {
    color: "#F59E0B",
    label: "Influenced By",
    icon: "clock",
    strokeDasharray: "10,5",
  },
  IS_A: {
    color: "#10B981",
    label: "Is A",
    icon: "arrow-up-right",
  },
  PART_OF: {
    color: "#3B82F6",
    label: "Part Of",
    icon: "box",
  },
  RELATED_TO: {
    color: "#EC4899",
    label: "Related To",
    icon: "refresh",
    strokeDasharray: "3,3",
  },
  DEPENDS_ON: {
    color: "#EF4444",
    label: "Depends On",
    icon: "zap",
  },
}

// Pre-computed entity type config (moved outside component)
const ENTITY_TYPE_CONFIG: Record<string, { color: string; icon: string; bg: string }> = {
  concept: {
    color: "border-blue-400",
    icon: "crystal",
    bg: "from-blue-500/20 to-blue-600/10",
  },
  system: {
    color: "border-green-400",
    icon: "gear",
    bg: "from-green-500/20 to-green-600/10",
  },
  person: {
    color: "border-purple-400",
    icon: "person",
    bg: "from-purple-500/20 to-purple-600/10",
  },
  technology: {
    color: "border-orange-400",
    icon: "wrench",
    bg: "from-orange-500/20 to-orange-600/10",
  },
  pattern: {
    color: "border-pink-400",
    icon: "target",
    bg: "from-pink-500/20 to-pink-600/10",
  },
}

// Custom node component for decisions - memoized (P1-1)
const DecisionNode = React.memo(
  function DecisionNode({ data, selected }: NodeProps) {
    const nodeData = data as { label: string; decision?: Decision & { source?: string }; hasEmbedding?: boolean; isFocused?: boolean }
    const source = nodeData.decision?.source || "unknown"
    const sourceStyle = SOURCE_STYLES[source] || SOURCE_STYLES.unknown
    const badgeStyle = SOURCE_BADGE_STYLES[source as keyof typeof SOURCE_BADGE_STYLES] || SOURCE_BADGE_STYLES.unknown
    const isFocused = nodeData.isFocused

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
          ${isFocused
            ? "ring-2 ring-cyan-400 ring-offset-2 ring-offset-slate-900"
            : ""
          }
        `}
        role="button"
        aria-label={`Decision node: ${nodeData.label}`}
        aria-pressed={selected}
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
            style={badgeStyle}
          >
            {sourceStyle.label}
          </Badge>
          {nodeData.hasEmbedding && (
            <span title="Has semantic embedding" aria-label="Has semantic embedding">
              <Sparkles className="h-3 w-3 text-purple-400" aria-hidden="true" />
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
            <TooltipContent side="top" className="max-w-lg">
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
            <TooltipContent side="bottom" className="max-w-lg">
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
  },
  // Custom comparison function for memoization (P1-1)
  (prev, next) => {
    const prevData = prev.data as { decision?: { id: string }; hasEmbedding?: boolean; isFocused?: boolean }
    const nextData = next.data as { decision?: { id: string }; hasEmbedding?: boolean; isFocused?: boolean }
    return prev.selected === next.selected && 
      prevData?.decision?.id === nextData?.decision?.id &&
      prevData?.hasEmbedding === nextData?.hasEmbedding &&
      prevData?.isFocused === nextData?.isFocused
  }
)

// Custom node component for entities - memoized (P1-1)
const EntityNode = React.memo(
  function EntityNode({ data, selected }: NodeProps) {
    const nodeData = data as { label: string; entity?: Entity; hasEmbedding?: boolean; isFocused?: boolean }
    const entityType = nodeData.entity?.type || "concept"
    const config = ENTITY_TYPE_CONFIG[entityType] || ENTITY_TYPE_CONFIG.concept
    const isFocused = nodeData.isFocused
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
          ${isFocused
            ? "ring-2 ring-cyan-400 ring-offset-2 ring-offset-slate-900"
            : ""
          }
        `}
        role="button"
        aria-label={`Entity node: ${nodeData.label}, type: ${entityType}`}
        aria-pressed={selected}
      >
        <Handle
          type="target"
          position={Position.Top}
          className="!w-2 !h-2 !bg-slate-400 !border-slate-700"
        />
        <div className="flex items-center gap-2">
          <span className="text-base" aria-hidden="true">
            {entityType === "concept" ? "crystal-ball" :
             entityType === "system" ? "gear" :
             entityType === "person" ? "person" :
             entityType === "technology" ? "wrench" : "target"}
          </span>
          <span className="font-medium text-sm text-slate-200 whitespace-nowrap">
            {nodeData.label}
          </span>
          {nodeData.hasEmbedding && (
            <span title="Has semantic embedding" aria-label="Has semantic embedding">
              <Sparkles className="h-3 w-3 text-purple-400" aria-hidden="true" />
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
  },
  // Custom comparison function for memoization (P1-1)
  (prev, next) => {
    const prevData = prev.data as { entity?: { id: string }; hasEmbedding?: boolean; isFocused?: boolean }
    const nextData = next.data as { entity?: { id: string }; hasEmbedding?: boolean; isFocused?: boolean }
    return prev.selected === next.selected && 
      prevData?.entity?.id === nextData?.entity?.id &&
      prevData?.hasEmbedding === nextData?.hasEmbedding &&
      prevData?.isFocused === nextData?.isFocused
  }
)

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
  onDeleteDecision?: (decisionId: string) => Promise<void>
}

// Inner component that uses useReactFlow hook (P0-3: Keyboard navigation)
function KnowledgeGraphInner({
  data,
  onNodeClick,
  sourceFilter,
  onSourceFilterChange,
  sourceCounts = {},
  onDeleteDecision,
}: KnowledgeGraphProps) {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)
  const [showRelationshipLegend, setShowRelationshipLegend] = useState(true)
  const [showSourceLegend, setShowSourceLegend] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { setCenter, getZoom } = useReactFlow()

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
          isFocused: false,
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
          isFocused: false,
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

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  // Update nodes when focusedNodeId changes to add focus indicator (P0-3)
  useEffect(() => {
    setNodes((prevNodes) =>
      prevNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          isFocused: node.id === focusedNodeId,
        },
      }))
    )
  }, [focusedNodeId, setNodes])

  // Count relationships by type
  const relationshipCounts = useMemo(() => {
    if (!data?.edges) return {}
    return data.edges.reduce((acc, edge) => {
      acc[edge.relationship] = (acc[edge.relationship] || 0) + 1
      return acc
    }, {} as Record<string, number>)
  }, [data])

  // Find the nearest node in a given direction (P0-3: Keyboard navigation)
  const findNearestNode = useCallback(
    (currentNode: Node, direction: "up" | "down" | "left" | "right"): Node | null => {
      if (nodes.length === 0) return null

      const currentPos = currentNode.position
      let nearestNode: Node | null = null
      let nearestDistance = Infinity

      for (const node of nodes) {
        if (node.id === currentNode.id) continue

        const nodePos = node.position
        const dx = nodePos.x - currentPos.x
        const dy = nodePos.y - currentPos.y

        // Check if node is in the correct direction
        let isInDirection = false
        switch (direction) {
          case "up":
            isInDirection = dy < -20 && Math.abs(dx) < Math.abs(dy) * 2
            break
          case "down":
            isInDirection = dy > 20 && Math.abs(dx) < Math.abs(dy) * 2
            break
          case "left":
            isInDirection = dx < -20 && Math.abs(dy) < Math.abs(dx) * 2
            break
          case "right":
            isInDirection = dx > 20 && Math.abs(dy) < Math.abs(dx) * 2
            break
        }

        if (isInDirection) {
          const distance = Math.sqrt(dx * dx + dy * dy)
          if (distance < nearestDistance) {
            nearestDistance = distance
            nearestNode = node
          }
        }
      }

      return nearestNode
    },
    [nodes]
  )

  // Center view on a node (P0-3: Keyboard navigation)
  const centerOnNode = useCallback(
    (node: Node) => {
      const zoom = getZoom()
      setCenter(node.position.x + 100, node.position.y + 50, { zoom, duration: 200 })
    },
    [setCenter, getZoom]
  )

  // Keyboard navigation handler (P0-3)
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return
      }

      switch (event.key) {
        case "ArrowUp":
        case "ArrowDown":
        case "ArrowLeft":
        case "ArrowRight": {
          event.preventDefault()
          const direction = event.key.replace("Arrow", "").toLowerCase() as
            | "up"
            | "down"
            | "left"
            | "right"

          // If no node is focused, focus the first node
          if (!focusedNodeId) {
            const firstNode = nodes[0]
            if (firstNode) {
              setFocusedNodeId(firstNode.id)
              centerOnNode(firstNode)
            }
            return
          }

          // Find the currently focused node
          const currentNode = nodes.find((n) => n.id === focusedNodeId)
          if (!currentNode) return

          // Find and focus the nearest node in the direction
          const nearestNode = findNearestNode(currentNode, direction)
          if (nearestNode) {
            setFocusedNodeId(nearestNode.id)
            centerOnNode(nearestNode)
          }
          break
        }

        case "Enter":
        case " ": {
          event.preventDefault()
          // Select the focused node (open detail panel)
          if (focusedNodeId) {
            const node = nodes.find((n) => n.id === focusedNodeId)
            if (node) {
              setSelectedNode(node)
              onNodeClick?.(node)
            }
          }
          break
        }

        case "Escape": {
          event.preventDefault()
          // Deselect node and clear focus
          if (selectedNode) {
            setSelectedNode(null)
          } else if (focusedNodeId) {
            setFocusedNodeId(null)
          }
          break
        }

        case "Tab": {
          // Let Tab work naturally for focus management
          // but if we are inside the graph, move to next node
          if (!event.shiftKey && focusedNodeId) {
            const currentIndex = nodes.findIndex((n) => n.id === focusedNodeId)
            const nextIndex = (currentIndex + 1) % nodes.length
            const nextNode = nodes[nextIndex]
            if (nextNode) {
              event.preventDefault()
              setFocusedNodeId(nextNode.id)
              centerOnNode(nextNode)
            }
          } else if (event.shiftKey && focusedNodeId) {
            const currentIndex = nodes.findIndex((n) => n.id === focusedNodeId)
            const prevIndex = currentIndex === 0 ? nodes.length - 1 : currentIndex - 1
            const prevNode = nodes[prevIndex]
            if (prevNode) {
              event.preventDefault()
              setFocusedNodeId(prevNode.id)
              centerOnNode(prevNode)
            }
          }
          break
        }

        case "Home": {
          event.preventDefault()
          // Focus first node
          const firstNode = nodes[0]
          if (firstNode) {
            setFocusedNodeId(firstNode.id)
            centerOnNode(firstNode)
          }
          break
        }

        case "End": {
          event.preventDefault()
          // Focus last node
          const lastNode = nodes[nodes.length - 1]
          if (lastNode) {
            setFocusedNodeId(lastNode.id)
            centerOnNode(lastNode)
          }
          break
        }
      }
    },
    [focusedNodeId, nodes, selectedNode, findNearestNode, centerOnNode, onNodeClick]
  )

  // Memoized event handlers (P1-4)
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node)
      setFocusedNodeId(node.id)
      onNodeClick?.(node)
    },
    [onNodeClick]
  )

  const closeDetailPanel = useCallback(() => setSelectedNode(null), [])

  const handleDeleteClick = useCallback((id: string, name: string) => {
    setDeleteTarget({ id, name })
  }, [])

  const handleDeleteConfirm = useCallback(async () => {
    if (deleteTarget && onDeleteDecision) {
      await onDeleteDecision(deleteTarget.id)
      setDeleteTarget(null)
      setSelectedNode(null)
    }
  }, [deleteTarget, onDeleteDecision])

  const handleSourceFilterClick = useCallback((source: string | null) => {
    onSourceFilterChange?.(source)
  }, [onSourceFilterChange])

  // Handle focus on container click
  const handleContainerFocus = useCallback(() => {
    if (!focusedNodeId && nodes.length > 0) {
      setFocusedNodeId(nodes[0].id)
    }
  }, [focusedNodeId, nodes])

  return (
    <div
      ref={containerRef}
      className="h-full w-full relative focus:outline-none"
      role="application"
      aria-label="Knowledge graph visualization. Use arrow keys to navigate between nodes, Enter to select, Escape to deselect."
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onFocus={handleContainerFocus}
    >
      {/* Screen reader instructions */}
      <div className="sr-only" aria-live="polite">
        {focusedNodeId
          ? `Focused on node: ${nodes.find((n) => n.id === focusedNodeId)?.data?.label || "unknown"}. Press Enter to view details, arrow keys to navigate.`
          : "Press Tab or arrow keys to start navigating the graph."}
      </div>

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
          aria-label="Graph controls"
        />
        <MiniMap
          nodeColor={(node) =>
            node.type === "decision" ? "#22D3EE" : "#64748B"
          }
          maskColor="rgba(15, 23, 42, 0.8)"
          className="!bg-slate-800/80 !border-white/10 !rounded-xl"
          aria-label="Graph minimap"
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
                  <Bot className="h-4 w-4" aria-hidden="true" /> Decision Sources
                </CardTitle>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowSourceLegend(false)}
                        className="h-6 w-6 text-slate-400 hover:text-slate-200"
                        aria-label="Close source legend"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Close panel</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </CardHeader>
              <CardContent className="py-2 px-4 space-y-1.5">
                {/* All sources button */}
                <button
                  onClick={() => handleSourceFilterClick(null)}
                  aria-pressed={!sourceFilter}
                  aria-label="Show all decision sources"
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                    !sourceFilter
                      ? "bg-white/10 border border-white/20"
                      : "hover:bg-white/5"
                  }`}
                >
                  <div className="w-4 h-4 rounded bg-gradient-to-br from-slate-600 to-slate-700 border border-white/20" aria-hidden="true" />
                  <span className="text-xs text-slate-300 flex-1 text-left">All Sources</span>
                  <Badge className="text-[9px] px-1.5 py-0 bg-slate-700 text-slate-300 border-slate-600">
                    {Object.values(sourceCounts).reduce((a, b) => a + b, 0)}
                  </Badge>
                </button>

                {/* Individual source filters */}
                {Object.entries(SOURCE_STYLES).map(([key, style]) => {
                  const count = sourceCounts[key] || 0
                  if (count === 0 && key !== "unknown") return null
                  const badgeStyle = SOURCE_BADGE_STYLES[key as keyof typeof SOURCE_BADGE_STYLES] || SOURCE_BADGE_STYLES.unknown
                  return (
                    <button
                      key={key}
                      onClick={() => handleSourceFilterClick(sourceFilter === key ? null : key)}
                      aria-pressed={sourceFilter === key}
                      aria-label={`Filter by ${style.label}`}
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
                          backgroundColor: badgeStyle.backgroundColor,
                          color: badgeStyle.color,
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
        <Panel position="top-left" className="m-4" style={{ marginTop: showSourceLegend ? "280px" : "0" }}>
          <Card className="w-52 bg-slate-800/90 backdrop-blur-xl border-white/10" role="region" aria-label="Entity types legend">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm text-slate-200 flex items-center gap-2">
                <span aria-hidden="true">chart</span> Entity Types
              </CardTitle>
            </CardHeader>
            <CardContent className="py-2 px-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-blue-500/20 border-2 border-blue-400" aria-hidden="true" />
                <span className="text-xs text-slate-300">crystal-ball Concept</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-green-500/20 border-2 border-green-400" aria-hidden="true" />
                <span className="text-xs text-slate-300">gear System</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-orange-500/20 border-2 border-orange-400" aria-hidden="true" />
                <span className="text-xs text-slate-300">wrench Technology</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-purple-500/20 border-2 border-purple-400" aria-hidden="true" />
                <span className="text-xs text-slate-300">person Person</span>
              </div>
              <div className="flex items-center gap-2 pt-1 border-t border-white/10 mt-2">
                <Sparkles className="h-4 w-4 text-purple-400" aria-hidden="true" />
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
                  <GitBranch className="h-4 w-4" aria-hidden="true" /> Relationships
                </CardTitle>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowRelationshipLegend(false)}
                        className="h-6 w-6 text-slate-400 hover:text-slate-200"
                        aria-label="Close relationship legend"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Close panel</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
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
                        aria-hidden="true"
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

        {/* Keyboard Navigation Help Panel */}
        <Panel position="bottom-left" className="m-4">
          <div className="px-3 py-2 rounded-lg bg-slate-800/80 backdrop-blur-xl border border-white/10 text-xs text-slate-400 space-y-1">
            <div>Arrow keys: Navigate | Enter: Select | Esc: Deselect</div>
            <div>Click and drag to pan | Scroll to zoom</div>
          </div>
        </Panel>

        {/* Stats Panel */}
        <Panel position="bottom-right" className="m-4">
          <div className="px-3 py-2 rounded-lg bg-slate-800/80 backdrop-blur-xl border border-white/10 text-xs text-slate-400 flex gap-4">
            <span>pin {data?.nodes?.length || 0} nodes</span>
            <span>link {data?.edges?.length || 0} edges</span>
          </div>
        </Panel>
      </ReactFlow>

      {/* Detail Panel */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-80 z-10" style={{ marginTop: showRelationshipLegend ? "220px" : "0" }}>
          <Card className="bg-slate-800/95 backdrop-blur-xl border-white/10 shadow-2xl">
            <CardHeader className="flex flex-row items-center justify-between py-3 border-b border-white/10">
              <CardTitle className="text-base text-slate-100 flex items-center gap-2">
                {selectedNode.type === "decision" ? "lightbulb" : "crystal-ball"}
                {selectedNode.type === "decision" ? "Decision" : "Entity"} Details
              </CardTitle>
              <div className="flex items-center gap-1">
                {selectedNode.type === "decision" && onDeleteDecision && (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            const decisionData = selectedNode.data as { decision?: Decision }
                            if (decisionData.decision) {
                              handleDeleteClick(decisionData.decision.id, decisionData.decision.trigger)
                            }
                          }}
                          className="h-8 w-8 text-slate-400 hover:text-red-400 hover:bg-red-500/10"
                          aria-label="Delete decision"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Delete this decision</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={closeDetailPanel}
                        className="h-8 w-8 text-slate-400 hover:text-slate-200 hover:bg-white/10"
                        aria-label="Close details panel"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Close panel</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
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
                          <Sparkles className="h-3 w-3" aria-hidden="true" />
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
                        <div className="flex flex-wrap gap-2" role="list" aria-label="Related entities">
                          {(decision.entities ?? []).length > 0 ? (
                            decision.entities.map((entity) => (
                              <Badge
                                key={entity.id}
                                className="bg-blue-500/20 text-blue-400 border-blue-500/30"
                                role="listitem"
                              >
                                gear {entity.name}
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
                          <Sparkles className="h-3 w-3" aria-hidden="true" />
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

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        itemType="Decision"
        itemName={deleteTarget?.name}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  )
}

// Wrapper component with ReactFlowProvider (P0-3: Keyboard navigation requires useReactFlow hook)
export function KnowledgeGraph(props: KnowledgeGraphProps) {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphInner {...props} />
    </ReactFlowProvider>
  )
}
