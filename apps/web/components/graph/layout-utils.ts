"use client"

import dagre from "dagre"
import type { Node, Edge } from "@xyflow/react"

export type LayoutType = "force" | "hierarchical" | "radial"

export interface LayoutOptions {
  type: LayoutType
  direction?: "TB" | "LR" | "BT" | "RL" // For hierarchical layout
  nodeSpacing?: number
  rankSpacing?: number
}

const DEFAULT_NODE_WIDTH = 280
const DEFAULT_NODE_HEIGHT = 100
const ENTITY_NODE_WIDTH = 150
const ENTITY_NODE_HEIGHT = 50

/**
 * Apply force-directed layout (simple grid-based layout that mimics force positioning)
 * This is a simplified version - the initial positions allow React Flow's built-in
 * physics to handle the rest when users interact with the graph
 */
export function applyForceLayout(
  nodes: Node[],
  edges: Edge[],
  options: { spacing?: number } = {}
): Node[] {
  const spacing = options.spacing ?? 500 // Increased from 400
  const decisionNodes = nodes.filter((n) => n.type === "decision")
  const entityNodes = nodes.filter((n) => n.type === "entity")

  const result: Node[] = []

  // Layout decisions in a row at the top with more spacing
  decisionNodes.forEach((node, index) => {
    result.push({
      ...node,
      position: {
        x: index * spacing + 150,
        y: 80,
      },
    })
  })

  // Layout entities in a grid below with much more spacing
  // Use fewer columns for more horizontal spread
  const cols = Math.max(2, Math.ceil(Math.sqrt(entityNodes.length * 0.6)))
  entityNodes.forEach((node, index) => {
    const row = Math.floor(index / cols)
    const col = index % cols
    result.push({
      ...node,
      position: {
        x: col * 350 + 200, // Increased from 200 to 350
        y: row * 200 + 400, // Increased from 120 to 200, start lower
      },
    })
  })

  return result
}

/**
 * Apply hierarchical layout using Dagre
 * Places nodes in a tree-like structure based on their connections
 */
export function applyHierarchicalLayout(
  nodes: Node[],
  edges: Edge[],
  options: { direction?: "TB" | "LR" | "BT" | "RL"; nodeSpacing?: number; rankSpacing?: number } = {}
): Node[] {
  const direction = options.direction ?? "TB"
  const nodeSpacing = options.nodeSpacing ?? 180 // Increased from 100
  const rankSpacing = options.rankSpacing ?? 250 // Increased from 150

  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}))

  g.setGraph({
    rankdir: direction,
    nodesep: nodeSpacing,
    ranksep: rankSpacing,
    marginx: 80,
    marginy: 80,
  })

  // Add nodes to the graph
  nodes.forEach((node) => {
    const width = node.type === "decision" ? DEFAULT_NODE_WIDTH : ENTITY_NODE_WIDTH
    const height = node.type === "decision" ? DEFAULT_NODE_HEIGHT : ENTITY_NODE_HEIGHT
    g.setNode(node.id, { width, height })
  })

  // Add edges to the graph
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  // Run the layout
  dagre.layout(g)

  // Apply the calculated positions
  return nodes.map((node) => {
    const nodeWithPos = g.node(node.id)
    const width = node.type === "decision" ? DEFAULT_NODE_WIDTH : ENTITY_NODE_WIDTH
    const height = node.type === "decision" ? DEFAULT_NODE_HEIGHT : ENTITY_NODE_HEIGHT

    return {
      ...node,
      position: {
        x: nodeWithPos.x - width / 2,
        y: nodeWithPos.y - height / 2,
      },
    }
  })
}

/**
 * Apply radial layout
 * Places decision nodes in the center with entities arranged in concentric circles
 */
export function applyRadialLayout(
  nodes: Node[],
  edges: Edge[],
  options: { centerRadius?: number; ringSpacing?: number } = {}
): Node[] {
  const decisionNodes = nodes.filter((n) => n.type === "decision")
  const entityNodes = nodes.filter((n) => n.type === "entity")

  // Dynamic radius based on number of nodes for better spacing
  const baseRadius = Math.max(300, decisionNodes.length * 80) // Increased from 200
  const centerRadius = options.centerRadius ?? baseRadius
  const ringSpacing = options.ringSpacing ?? 280 // Increased from 150

  const centerX = 600
  const centerY = 500

  const result: Node[] = []

  // Place decision nodes in the center (inner circle)
  if (decisionNodes.length === 1) {
    // Single decision at center
    result.push({
      ...decisionNodes[0],
      position: { x: centerX - DEFAULT_NODE_WIDTH / 2, y: centerY - DEFAULT_NODE_HEIGHT / 2 },
    })
  } else {
    // Multiple decisions in inner circle with adequate spacing
    const decisionAngleStep = (2 * Math.PI) / decisionNodes.length
    decisionNodes.forEach((node, index) => {
      const angle = index * decisionAngleStep - Math.PI / 2 // Start from top
      result.push({
        ...node,
        position: {
          x: centerX + centerRadius * Math.cos(angle) - DEFAULT_NODE_WIDTH / 2,
          y: centerY + centerRadius * Math.sin(angle) - DEFAULT_NODE_HEIGHT / 2,
        },
      })
    })
  }

  // Group entities by their connected decisions for better placement
  const entityConnections = new Map<string, Set<string>>()
  edges.forEach((edge) => {
    const entityId = entityNodes.find((n) => n.id === edge.source || n.id === edge.target)?.id
    const decisionId = decisionNodes.find((n) => n.id === edge.source || n.id === edge.target)?.id
    if (entityId && decisionId) {
      if (!entityConnections.has(entityId)) {
        entityConnections.set(entityId, new Set())
      }
      entityConnections.get(entityId)?.add(decisionId)
    }
  })

  // Place entities in outer ring(s) with dynamic ring count based on entity count
  const maxEntitiesPerRing = Math.max(8, Math.ceil(entityNodes.length / 2))
  const numRings = Math.ceil(entityNodes.length / maxEntitiesPerRing)

  entityNodes.forEach((node, index) => {
    const ringIndex = Math.floor(index / maxEntitiesPerRing)
    const indexInRing = index % maxEntitiesPerRing
    const entitiesInThisRing = Math.min(maxEntitiesPerRing, entityNodes.length - ringIndex * maxEntitiesPerRing)

    const outerRadius = centerRadius + ringSpacing * (ringIndex + 1)
    const angleStep = (2 * Math.PI) / entitiesInThisRing
    const angle = indexInRing * angleStep - Math.PI / 2

    result.push({
      ...node,
      position: {
        x: centerX + outerRadius * Math.cos(angle) - ENTITY_NODE_WIDTH / 2,
        y: centerY + outerRadius * Math.sin(angle) - ENTITY_NODE_HEIGHT / 2,
      },
    })
  })

  return result
}

/**
 * Main layout function that dispatches to the appropriate layout algorithm
 */
export function applyLayout(
  nodes: Node[],
  edges: Edge[],
  layoutType: LayoutType,
  options: LayoutOptions = { type: "force" }
): Node[] {
  switch (layoutType) {
    case "hierarchical":
      return applyHierarchicalLayout(nodes, edges, {
        direction: options.direction ?? "TB",
        nodeSpacing: options.nodeSpacing ?? 180, // Increased from 100
        rankSpacing: options.rankSpacing ?? 250, // Increased from 150
      })
    case "radial":
      return applyRadialLayout(nodes, edges)
    case "force":
    default:
      return applyForceLayout(nodes, edges)
  }
}

/**
 * Edge bundling - groups edges by relationship type and adjusts their paths
 * to reduce visual clutter. Returns edge updates with curvature adjustments.
 */
export function bundleEdges(edges: Edge[]): Edge[] {
  // Group edges by source-target pairs
  const edgeGroups = new Map<string, Edge[]>()
  
  edges.forEach((edge) => {
    // Create a normalized key for parallel edges (regardless of direction)
    const key = [edge.source, edge.target].sort().join("->")
    if (!edgeGroups.has(key)) {
      edgeGroups.set(key, [])
    }
    edgeGroups.get(key)?.push(edge)
  })

  const bundledEdges: Edge[] = []

  edgeGroups.forEach((group) => {
    if (group.length === 1) {
      // Single edge, no bundling needed
      bundledEdges.push(group[0])
    } else {
      // Multiple edges between same nodes - apply curvature to separate them
      const midIndex = (group.length - 1) / 2
      group.forEach((edge, index) => {
        // Calculate curvature offset: edges spread out from center
        const offset = (index - midIndex) * 0.3
        bundledEdges.push({
          ...edge,
          // Use smoothstep edge type for better curves
          type: "smoothstep",
          style: {
            ...edge.style,
          },
          // Store curvature in data for potential custom edge rendering
          data: {
            ...edge.data,
            bundleOffset: offset,
            bundleIndex: index,
            bundleSize: group.length,
          },
        })
      })
    }
  })

  return bundledEdges
}

/**
 * Layout information for display
 */
export const LAYOUT_INFO: Record<LayoutType, { label: string; description: string; icon: string }> = {
  force: {
    label: "Force-Directed",
    description: "Natural clustering with physics-based positioning",
    icon: "scatter-chart",
  },
  hierarchical: {
    label: "Hierarchical",
    description: "Tree-like structure showing decision hierarchy",
    icon: "git-branch",
  },
  radial: {
    label: "Radial",
    description: "Decisions at center, entities in outer rings",
    icon: "target",
  },
}
