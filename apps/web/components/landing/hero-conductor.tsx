"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

// ── Chat messages (human ↔ AI conversation on the laptop screen) ────

const CHAT_MESSAGES = [
  { role: "human" as const, text: "I need to migrate from SQLite to PostgreSQL" },
  { role: "ai" as const, text: "I'll set up PostgreSQL with async SQLAlchemy and add a Redis caching layer for frequently accessed queries." },
  { role: "human" as const, text: "Why Redis over Memcached?" },
  { role: "ai" as const, text: "Redis supports data structures we need for the entity resolution cache — sorted sets for similarity scores." },
];

// ── Graph nodes that the conversation transforms into ───────────────

interface GraphNode {
  id: number;
  kind: "decision" | "entity";
  label: string;
  entityType?: "technology" | "pattern";
  /** Final position (relative to graph container center) */
  x: number;
  y: number;
}

const GRAPH_NODES: GraphNode[] = [
  { id: 0, kind: "decision", label: "Use PostgreSQL", x: -180, y: -80 },
  { id: 1, kind: "decision", label: "Add Redis Caching", x: 160, y: -60 },
  { id: 2, kind: "entity", entityType: "technology", label: "PostgreSQL", x: -260, y: 40 },
  { id: 3, kind: "entity", entityType: "technology", label: "Redis", x: 280, y: 50 },
  { id: 4, kind: "entity", entityType: "technology", label: "SQLAlchemy", x: -60, y: 60 },
  { id: 5, kind: "entity", entityType: "pattern", label: "Async Pattern", x: 60, y: -120 },
];

interface GraphEdge {
  source: number;
  target: number;
  label: string;
  dashed?: boolean;
}

const GRAPH_EDGES: GraphEdge[] = [
  { source: 0, target: 2, label: "INVOLVES" },
  { source: 0, target: 4, label: "INVOLVES" },
  { source: 1, target: 3, label: "INVOLVES" },
  { source: 1, target: 5, label: "INVOLVES" },
  { source: 1, target: 0, label: "SUPERSEDES", dashed: true },
];

// ── Colour helpers ──────────────────────────────────────────────────

function nodeColor(node: GraphNode): string {
  if (node.kind === "decision") return "rgba(139,92,246,0.9)";
  switch (node.entityType) {
    case "technology": return "rgba(251,146,60,0.9)";
    case "pattern": return "rgba(236,72,153,0.9)";
    default: return "rgba(139,92,246,0.9)";
  }
}

function nodeBg(node: GraphNode): string {
  if (node.kind === "decision") return "rgba(139,92,246,0.08)";
  switch (node.entityType) {
    case "technology": return "rgba(251,146,60,0.08)";
    case "pattern": return "rgba(236,72,153,0.08)";
    default: return "rgba(139,92,246,0.08)";
  }
}

function nodeBorder(node: GraphNode): string {
  if (node.kind === "decision") return "rgba(139,92,246,0.4)";
  switch (node.entityType) {
    case "technology": return "rgba(251,146,60,0.3)";
    case "pattern": return "rgba(236,72,153,0.3)";
    default: return "rgba(139,92,246,0.4)";
  }
}

// ── Sub-components (to use hooks inside .map) ───────────────────────

function EdgeLabel({
  x,
  y,
  label,
  scrollYProgress,
}: {
  x: number;
  y: number;
  label: string;
  scrollYProgress: import("framer-motion").MotionValue<number>;
}) {
  const opacity = useTransform(scrollYProgress, [0.6, 0.75], [0, 0.5]);
  return (
    <motion.text
      x={x}
      y={y}
      textAnchor="middle"
      fill="rgba(255,255,255,0.4)"
      fontSize="8"
      fontFamily="'Instrument Sans', sans-serif"
      style={{ opacity }}
    >
      {label}
    </motion.text>
  );
}

function GraphNodePill({
  node,
  index,
  scrollYProgress,
}: {
  node: GraphNode;
  index: number;
  scrollYProgress: import("framer-motion").MotionValue<number>;
}) {
  const left = 350 + node.x;
  const top = 200 + node.y;
  const isDecision = node.kind === "decision";
  const nodeOpacity = useTransform(
    scrollYProgress,
    [0.42 + index * 0.03, 0.52 + index * 0.03],
    [0, 1]
  );
  const nodeScale = useTransform(
    scrollYProgress,
    [0.42 + index * 0.03, 0.52 + index * 0.03],
    [0.5, 1]
  );

  return (
    <motion.div
      className="absolute flex items-center justify-center whitespace-nowrap"
      style={{
        left: `${left}px`,
        top: `${top}px`,
        x: "-50%",
        y: "-50%",
        opacity: nodeOpacity,
        scale: nodeScale,
      }}
    >
      <div
        className={`px-3 py-1.5 rounded-full border text-[10px] font-medium ${
          isDecision ? "rounded-xl" : ""
        }`}
        style={{
          background: nodeBg(node),
          borderColor: nodeBorder(node),
          color: nodeColor(node),
        }}
      >
        {node.label}
      </div>
    </motion.div>
  );
}

// ── Component ───────────────────────────────────────────────────────

export function HeroConductor() {
  const containerRef = useRef<HTMLDivElement>(null);

  // Track scroll progress through the entire hero container (0 → 1)
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"],
  });

  // ── Scroll-mapped transforms ──────────────────────────────────
  // 0.0 → 0.3: Developer + laptop with conversation visible
  // 0.3 → 0.6: Conversation flows out of screen, transforms into graph
  // 0.6 → 1.0: Graph fully formed, tagline appears

  // Developer + laptop
  const devOpacity = useTransform(scrollYProgress, [0, 0.15, 0.5, 0.7], [0, 1, 1, 0]);
  const devY = useTransform(scrollYProgress, [0, 0.15], [60, 0]);

  // Chat messages (staggered appearance, then flow upward)
  const chatOpacity = useTransform(scrollYProgress, [0.05, 0.15, 0.35, 0.5], [0, 1, 1, 0]);
  const chatY = useTransform(scrollYProgress, [0.35, 0.55], [0, -200]);

  // Laptop screen glow intensifies as conversation happens
  const screenGlow = useTransform(scrollYProgress, [0.1, 0.25, 0.5], [0.3, 0.7, 0.2]);

  // Graph nodes (appear as chat disappears)
  const graphOpacity = useTransform(scrollYProgress, [0.4, 0.55, 0.9, 1.0], [0, 1, 1, 0.8]);
  const graphScale = useTransform(scrollYProgress, [0.4, 0.6], [0.6, 1]);

  // Graph edges draw in
  const edgeProgress = useTransform(scrollYProgress, [0.5, 0.7], [0, 1]);

  // Tagline
  const taglineOpacity = useTransform(scrollYProgress, [0.65, 0.8], [0, 1]);
  const taglineY = useTransform(scrollYProgress, [0.65, 0.8], [30, 0]);

  // Light trails (from laptop to graph)
  const trailOpacity = useTransform(scrollYProgress, [0.35, 0.45, 0.65, 0.75], [0, 0.8, 0.8, 0]);
  const trailLength = useTransform(scrollYProgress, [0.35, 0.6], [0, 1]);

  return (
    <div
      ref={containerRef}
      className="relative"
      style={{ height: "250vh" }}
    >
      {/* Sticky viewport — stays fixed while user scrolls through the 250vh container */}
      <div className="sticky top-0 h-screen w-full overflow-hidden flex items-center justify-center">
        {/* Background */}
        <div className="absolute inset-0 bg-[hsl(250,20%,6%)]" />

        {/* Nebula orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
          <div className="absolute top-1/4 left-[16%] w-72 h-72 bg-violet-500/[0.08] rounded-full blur-3xl animate-float" />
          <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-fuchsia-500/[0.05] rounded-full blur-3xl animate-float [animation-delay:-1.5s]" />
          <div className="absolute top-1/2 right-[16%] w-56 h-56 bg-orange-500/[0.04] rounded-full blur-3xl animate-float [animation-delay:-3s]" />
        </div>

        {/* ── Developer at laptop ──────────────────────────────── */}
        <motion.div
          className="absolute bottom-[8%] left-1/2 -translate-x-1/2"
          style={{ opacity: devOpacity, y: devY }}
        >
          {/* Developer silhouette — clean SVG from behind */}
          <svg
            width="340"
            height="300"
            viewBox="0 0 340 300"
            fill="none"
            className="mx-auto"
            aria-hidden="true"
          >
            {/* Back of head */}
            <ellipse cx="170" cy="60" rx="30" ry="34" fill="rgba(20,15,40,0.9)" stroke="rgba(139,92,246,0.15)" strokeWidth="1" />
            {/* Hair detail */}
            <path d="M 145 50 Q 158 35 170 32 Q 182 35 195 50" fill="none" stroke="rgba(139,92,246,0.2)" strokeWidth="1.5" strokeLinecap="round" />
            {/* Neck */}
            <rect x="161" y="92" width="18" height="14" fill="rgba(20,15,40,0.9)" />
            {/* Shoulders + torso */}
            <path
              d="M 100 120 Q 130 106 161 106 L 179 106 Q 210 106 240 120 L 240 210 Q 238 230 230 240 L 110 240 Q 102 230 100 210 Z"
              fill="rgba(20,15,40,0.9)"
              stroke="rgba(139,92,246,0.1)"
              strokeWidth="1"
            />
            {/* Left arm resting on desk */}
            <path
              d="M 100 120 Q 80 135 70 160 Q 62 180 65 195"
              fill="none"
              stroke="rgba(20,15,40,0.9)"
              strokeWidth="16"
              strokeLinecap="round"
            />
            <path
              d="M 100 120 Q 80 135 70 160 Q 62 180 65 195"
              fill="none"
              stroke="rgba(139,92,246,0.1)"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
            {/* Right arm resting on desk */}
            <path
              d="M 240 120 Q 260 135 270 160 Q 278 180 275 195"
              fill="none"
              stroke="rgba(20,15,40,0.9)"
              strokeWidth="16"
              strokeLinecap="round"
            />
            <path
              d="M 240 120 Q 260 135 270 160 Q 278 180 275 195"
              fill="none"
              stroke="rgba(139,92,246,0.1)"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
            {/* Desk surface */}
            <rect x="30" y="200" width="280" height="6" rx="2" fill="rgba(30,25,55,0.8)" stroke="rgba(139,92,246,0.08)" strokeWidth="1" />
            {/* Laptop base on desk */}
            <path d="M 90 200 L 80 196 L 260 196 L 250 200 Z" fill="rgba(30,25,55,0.9)" stroke="rgba(139,92,246,0.12)" strokeWidth="0.8" />
          </svg>

          {/* Laptop screen — positioned overlapping the SVG */}
          <div
            className="absolute left-1/2 -translate-x-1/2 w-[220px] h-[140px] rounded-md border border-violet-500/20 overflow-hidden"
            style={{ bottom: "105px" }}
          >
            {/* Screen glow */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-b from-violet-500/20 to-violet-900/10"
              style={{ opacity: screenGlow }}
            />
            <div className="absolute inset-0 bg-[hsl(250,20%,4%)]" />

            {/* Chat conversation on screen */}
            <motion.div
              className="relative z-10 p-2 flex flex-col gap-1.5 text-[7px] leading-tight"
              style={{ opacity: chatOpacity, y: chatY }}
            >
              {CHAT_MESSAGES.map((msg, i) => (
                <div
                  key={i}
                  className={`rounded px-1.5 py-1 max-w-[85%] ${
                    msg.role === "human"
                      ? "self-end bg-violet-500/15 text-violet-200/80 border border-violet-500/20"
                      : "self-start bg-white/[0.04] text-slate-300/70 border border-white/[0.06]"
                  }`}
                >
                  <span className="block text-[5px] font-medium mb-0.5 opacity-50">
                    {msg.role === "human" ? "You" : "Claude"}
                  </span>
                  {msg.text}
                </div>
              ))}
            </motion.div>
          </div>
        </motion.div>

        {/* ── Light trails (laptop → graph) ────────────────────── */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
          <defs>
            <linearGradient id="hc-trail-l" x1="40%" y1="80%" x2="20%" y2="30%" gradientUnits="objectBoundingBox">
              <stop offset="0%" stopColor="rgba(139,92,246,0.6)" />
              <stop offset="50%" stopColor="rgba(236,72,153,0.3)" />
              <stop offset="100%" stopColor="rgba(251,146,60,0.1)" />
            </linearGradient>
            <linearGradient id="hc-trail-r" x1="60%" y1="80%" x2="80%" y2="30%" gradientUnits="objectBoundingBox">
              <stop offset="0%" stopColor="rgba(139,92,246,0.6)" />
              <stop offset="50%" stopColor="rgba(236,72,153,0.3)" />
              <stop offset="100%" stopColor="rgba(251,146,60,0.1)" />
            </linearGradient>
          </defs>
          {/* Left trail */}
          <motion.path
            d="M 50% 70% Q 35% 55%, 30% 40%"
            fill="none"
            stroke="url(#hc-trail-l)"
            strokeWidth="2.5"
            strokeLinecap="round"
            pathLength="1"
            style={{
              pathLength: trailLength,
              opacity: trailOpacity,
            }}
          />
          {/* Right trail */}
          <motion.path
            d="M 50% 70% Q 65% 55%, 70% 40%"
            fill="none"
            stroke="url(#hc-trail-r)"
            strokeWidth="2.5"
            strokeLinecap="round"
            pathLength="1"
            style={{
              pathLength: trailLength,
              opacity: trailOpacity,
            }}
          />
        </svg>

        {/* ── Knowledge Graph (forms from conversation) ────────── */}
        <motion.div
          className="absolute top-[15%] left-1/2 -translate-x-1/2 w-[700px] h-[400px]"
          style={{ opacity: graphOpacity, scale: graphScale }}
        >
          {/* Edges (SVG lines between nodes) */}
          <svg className="absolute inset-0 w-full h-full" aria-hidden="true">
            {GRAPH_EDGES.map((edge, i) => {
              const sNode = GRAPH_NODES[edge.source];
              const tNode = GRAPH_NODES[edge.target];
              // Node positions are relative to center of container (350, 200)
              const sx = 350 + sNode.x;
              const sy = 200 + sNode.y;
              const tx = 350 + tNode.x;
              const ty = 200 + tNode.y;

              return (
                <g key={`edge-${i}`}>
                  <motion.line
                    x1={sx}
                    y1={sy}
                    x2={tx}
                    y2={ty}
                    stroke={edge.dashed ? "rgba(236,72,153,0.4)" : "rgba(139,92,246,0.3)"}
                    strokeWidth={1}
                    strokeDasharray={edge.dashed ? "6 4" : "none"}
                    pathLength="1"
                    style={{
                      pathLength: edgeProgress,
                    }}
                  />
                  {/* Edge label */}
                  <EdgeLabel
                    x={(sx + tx) / 2}
                    y={(sy + ty) / 2 - 6}
                    label={edge.label}
                    scrollYProgress={scrollYProgress}
                  />
                </g>
              );
            })}
          </svg>

          {/* Nodes */}
          {GRAPH_NODES.map((node, i) => (
            <GraphNodePill
              key={`node-${node.id}`}
              node={node}
              index={i}
              scrollYProgress={scrollYProgress}
            />
          ))}
        </motion.div>

        {/* ── Tagline (appears after graph) ────────────────────── */}
        <motion.div
          className="absolute bottom-[20%] left-1/2 -translate-x-1/2 text-center"
          style={{ opacity: taglineOpacity, y: taglineY }}
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-tight">
            Decisions, by{" "}
            <span className="text-violet-400">you</span>
            {" + "}
            <span className="gradient-text">your agent</span>
            ,
            <br />
            <span className="gradient-text">remembered.</span>
          </h2>
        </motion.div>
      </div>
    </div>
  );
}
