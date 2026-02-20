"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Sparkles } from "lucide-react";

// ── Chat messages (human ↔ AI conversation on the laptop screen) ────

const CHAT_MESSAGES = [
  { role: "human" as const, text: "I need to migrate from SQLite to PostgreSQL" },
  { role: "ai" as const, text: "I'll set up PostgreSQL with async SQLAlchemy and add a Redis caching layer for queries." },
  { role: "human" as const, text: "Why Redis over Memcached?" },
  { role: "ai" as const, text: "Redis supports sorted sets we need for the entity resolution cache." },
];

// ── Graph nodes that the conversation transforms into ───────────────

interface GraphNode {
  id: number;
  kind: "decision" | "entity";
  label: string;
  entityType?: "technology" | "pattern";
  x: number;
  y: number;
}

const GRAPH_NODES: GraphNode[] = [
  { id: 0, kind: "decision", label: "Use PostgreSQL", x: -200, y: -80 },
  { id: 1, kind: "decision", label: "Add Redis Caching", x: 170, y: -60 },
  { id: 2, kind: "entity", entityType: "technology", label: "PostgreSQL", x: -280, y: 50 },
  { id: 3, kind: "entity", entityType: "technology", label: "Redis", x: 290, y: 50 },
  { id: 4, kind: "entity", entityType: "technology", label: "SQLAlchemy", x: -60, y: 70 },
  { id: 5, kind: "entity", entityType: "pattern", label: "Async Pattern", x: 60, y: -130 },
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
  return node.entityType === "technology"
    ? "rgba(251,146,60,0.9)"
    : "rgba(236,72,153,0.9)";
}

function nodeBg(node: GraphNode): string {
  if (node.kind === "decision") return "rgba(139,92,246,0.08)";
  return node.entityType === "technology"
    ? "rgba(251,146,60,0.08)"
    : "rgba(236,72,153,0.08)";
}

function nodeBorder(node: GraphNode): string {
  if (node.kind === "decision") return "rgba(139,92,246,0.4)";
  return node.entityType === "technology"
    ? "rgba(251,146,60,0.3)"
    : "rgba(236,72,153,0.3)";
}

// ── Sub-components (extract useTransform calls out of .map) ─────────

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
  const opacity = useTransform(scrollYProgress, [0.65, 0.8], [0, 0.5]);
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
  const delay = index * 0.03;
  const nodeOpacity = useTransform(
    scrollYProgress,
    [0.42 + delay, 0.55 + delay],
    [0, 1]
  );
  const nodeScale = useTransform(
    scrollYProgress,
    [0.42 + delay, 0.55 + delay],
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
        className={`px-3 py-1.5 rounded-full border text-[11px] font-medium ${
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

  // "end end" maps scrollYProgress 0→1 to exactly the range where
  // the sticky viewport is pinned (container height − viewport height).
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  // ── Scroll-mapped transforms ──────────────────────────────────
  // 0.00 → 0.35  Developer + laptop with conversation VISIBLE
  // 0.35 → 0.65  Conversation flows out, graph materializes
  // 0.65 → 1.00  Graph settled, tagline appears

  // Developer + laptop — VISIBLE FROM START (opacity 1 at scroll 0)
  const devOpacity = useTransform(scrollYProgress, [0, 0.5, 0.7], [1, 1, 0]);
  const devScale = useTransform(scrollYProgress, [0.4, 0.7], [1, 0.85]);

  // Chat messages — VISIBLE FROM START, float up & fade mid-scroll
  const chatOpacity = useTransform(scrollYProgress, [0, 0.3, 0.5], [1, 1, 0]);
  const chatY = useTransform(scrollYProgress, [0.25, 0.55], [0, -140]);

  // Laptop screen glow — starts visible
  const screenGlow = useTransform(scrollYProgress, [0, 0.2, 0.55], [0.5, 0.7, 0.1]);

  // Eyebrow badge — visible on load, fades with scroll
  const badgeOpacity = useTransform(scrollYProgress, [0, 0.12, 0.25], [1, 1, 0]);

  // Light trails (laptop → graph area) — bridging transition
  const trailOpacity = useTransform(scrollYProgress, [0.25, 0.35, 0.6, 0.72], [0, 0.7, 0.7, 0]);
  const trailLength = useTransform(scrollYProgress, [0.25, 0.6], [0, 1]);

  // Graph nodes — appear as chat fades
  const graphOpacity = useTransform(scrollYProgress, [0.4, 0.58, 1.0], [0, 1, 1]);
  const graphScale = useTransform(scrollYProgress, [0.4, 0.62], [0.7, 1]);

  // Graph edges — draw in after nodes appear
  const edgeProgress = useTransform(scrollYProgress, [0.52, 0.72], [0, 1]);

  // Tagline — appears last
  const taglineOpacity = useTransform(scrollYProgress, [0.72, 0.88], [0, 1]);
  const taglineY = useTransform(scrollYProgress, [0.72, 0.88], [30, 0]);

  return (
    <div
      ref={containerRef}
      className="relative"
      style={{ height: "250vh" }}
    >
      {/* Sticky viewport — stays fixed while user scrolls through 250vh container */}
      <div className="sticky top-0 h-screen w-full overflow-hidden flex items-center justify-center">
        {/* Background */}
        <div className="absolute inset-0 bg-[hsl(250,20%,6%)]" />

        {/* Nebula orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
          <div className="absolute top-1/4 left-[16%] w-72 h-72 bg-violet-500/[0.08] rounded-full blur-3xl animate-float" />
          <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-fuchsia-500/[0.05] rounded-full blur-3xl animate-float [animation-delay:-1.5s]" />
          <div className="absolute top-1/2 right-[16%] w-56 h-56 bg-orange-500/[0.04] rounded-full blur-3xl animate-float [animation-delay:-3s]" />
        </div>

        {/* ── Eyebrow badge — visible on load ──────────────────── */}
        <motion.div
          className="absolute top-[12%] left-1/2 -translate-x-1/2 text-center z-10"
          style={{ opacity: badgeOpacity }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-violet-500/20 bg-violet-500/5 text-sm text-violet-300">
            <Sparkles className="w-4 h-4" />
            Knowledge Graph for AI Decisions
          </div>
        </motion.div>

        {/* ── Developer at laptop — visible from start ─────────── */}
        <motion.div
          className="absolute bottom-[8%] left-1/2"
          style={{ opacity: devOpacity, scale: devScale, x: "-50%" }}
        >
          {/* Aura glow behind developer */}
          <div
            className="absolute left-1/2 -translate-x-1/2 w-[500px] h-[400px] rounded-full bg-violet-500/[0.07] blur-3xl pointer-events-none"
            style={{ bottom: "20px" }}
            aria-hidden="true"
          />

          {/* Developer silhouette SVG */}
          <svg
            width="440"
            height="360"
            viewBox="0 0 440 360"
            fill="none"
            className="relative mx-auto"
            aria-hidden="true"
          >
            {/* Radial aura behind the figure */}
            <defs>
              <radialGradient id="dev-aura" cx="50%" cy="45%" r="50%">
                <stop offset="0%" stopColor="rgba(139,92,246,0.12)" />
                <stop offset="100%" stopColor="rgba(139,92,246,0)" />
              </radialGradient>
            </defs>
            <ellipse cx="220" cy="170" rx="200" ry="170" fill="url(#dev-aura)" />

            {/* Head */}
            <ellipse
              cx="220" cy="75" rx="34" ry="38"
              fill="rgba(45,38,80,0.95)"
              stroke="rgba(139,92,246,0.35)"
              strokeWidth="1.2"
            />
            {/* Hair detail */}
            <path
              d="M 190 62 Q 205 44 220 40 Q 235 44 250 62"
              fill="none" stroke="rgba(139,92,246,0.4)" strokeWidth="1.5" strokeLinecap="round"
            />
            {/* Neck */}
            <rect x="210" y="111" width="20" height="16" fill="rgba(45,38,80,0.95)" />
            {/* Shoulders + torso */}
            <path
              d="M 140 135 Q 175 120 210 120 L 230 120 Q 265 120 300 135 L 300 260 Q 298 275 290 280 L 150 280 Q 142 275 140 260 Z"
              fill="rgba(45,38,80,0.95)"
              stroke="rgba(139,92,246,0.25)"
              strokeWidth="1"
            />
            {/* Jacket collar */}
            <path
              d="M 200 120 L 220 140 L 240 120"
              fill="none" stroke="rgba(139,92,246,0.25)" strokeWidth="1"
            />
            {/* Shoulder highlight */}
            <path
              d="M 140 135 Q 175 126 210 123"
              fill="none" stroke="rgba(139,92,246,0.18)" strokeWidth="0.8"
            />
            <path
              d="M 300 135 Q 265 126 230 123"
              fill="none" stroke="rgba(139,92,246,0.18)" strokeWidth="0.8"
            />
            {/* Left arm */}
            <path
              d="M 140 135 Q 115 155 105 185 Q 98 210 100 240"
              fill="none" stroke="rgba(45,38,80,0.95)" strokeWidth="18" strokeLinecap="round"
            />
            <path
              d="M 140 135 Q 115 155 105 185 Q 98 210 100 240"
              fill="none" stroke="rgba(139,92,246,0.25)" strokeWidth="1.2" strokeLinecap="round"
            />
            {/* Right arm */}
            <path
              d="M 300 135 Q 325 155 335 185 Q 342 210 340 240"
              fill="none" stroke="rgba(45,38,80,0.95)" strokeWidth="18" strokeLinecap="round"
            />
            <path
              d="M 300 135 Q 325 155 335 185 Q 342 210 340 240"
              fill="none" stroke="rgba(139,92,246,0.25)" strokeWidth="1.2" strokeLinecap="round"
            />
            {/* Desk surface */}
            <rect
              x="50" y="248" width="340" height="5" rx="2"
              fill="rgba(50,42,85,0.9)" stroke="rgba(139,92,246,0.15)" strokeWidth="1"
            />
            {/* Laptop base on desk */}
            <path
              d="M 120 248 L 110 243 L 330 243 L 320 248 Z"
              fill="rgba(50,42,85,0.95)" stroke="rgba(139,92,246,0.2)" strokeWidth="0.8"
            />
          </svg>

          {/* Laptop screen — positioned over the silhouette */}
          <div
            className="absolute left-1/2 -translate-x-1/2 w-[280px] h-[170px] rounded-lg border border-violet-500/30 overflow-hidden"
            style={{ bottom: "115px" }}
          >
            {/* Screen glow layer */}
            <motion.div
              className="absolute inset-0 bg-gradient-to-b from-violet-500/25 to-violet-900/10"
              style={{ opacity: screenGlow }}
            />
            {/* Dark screen bg */}
            <div className="absolute inset-0 bg-[hsl(250,20%,5%)]" />

            {/* Chat conversation on screen */}
            <motion.div
              className="relative z-10 p-3 flex flex-col gap-2 text-[9px] leading-snug"
              style={{ opacity: chatOpacity, y: chatY }}
            >
              {CHAT_MESSAGES.map((msg, i) => (
                <div
                  key={i}
                  className={`rounded-md px-2 py-1.5 max-w-[85%] ${
                    msg.role === "human"
                      ? "self-end bg-violet-500/15 text-violet-200/90 border border-violet-500/25"
                      : "self-start bg-white/[0.06] text-slate-300/80 border border-white/[0.08]"
                  }`}
                >
                  <span className="block text-[6px] font-semibold mb-0.5 opacity-60 uppercase tracking-wider">
                    {msg.role === "human" ? "You" : "Claude"}
                  </span>
                  {msg.text}
                </div>
              ))}
            </motion.div>
          </div>
        </motion.div>

        {/* ── Light trails (laptop → graph) ────────────────────── */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 1000 800"
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="hc-trail-l" x1="0.5" y1="0.75" x2="0.25" y2="0.3">
              <stop offset="0%" stopColor="rgba(139,92,246,0.6)" />
              <stop offset="50%" stopColor="rgba(236,72,153,0.3)" />
              <stop offset="100%" stopColor="rgba(251,146,60,0.1)" />
            </linearGradient>
            <linearGradient id="hc-trail-r" x1="0.5" y1="0.75" x2="0.75" y2="0.3">
              <stop offset="0%" stopColor="rgba(139,92,246,0.6)" />
              <stop offset="50%" stopColor="rgba(236,72,153,0.3)" />
              <stop offset="100%" stopColor="rgba(251,146,60,0.1)" />
            </linearGradient>
          </defs>
          {/* Left trail */}
          <motion.path
            d="M 500 580 Q 380 440, 310 280"
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
            d="M 500 580 Q 620 440, 690 280"
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
          className="absolute top-[12%] left-1/2 -translate-x-1/2 w-[700px] h-[400px]"
          style={{ opacity: graphOpacity, scale: graphScale }}
        >
          {/* Edges (SVG lines between nodes) */}
          <svg className="absolute inset-0 w-full h-full" aria-hidden="true">
            {GRAPH_EDGES.map((edge, i) => {
              const sNode = GRAPH_NODES[edge.source];
              const tNode = GRAPH_NODES[edge.target];
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
                    style={{ pathLength: edgeProgress }}
                  />
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
          className="absolute bottom-[18%] left-1/2 -translate-x-1/2 text-center"
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
