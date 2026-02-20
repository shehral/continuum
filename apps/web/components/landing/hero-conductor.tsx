"use client";

import { useState, useEffect } from "react";

// ── Data types ──────────────────────────────────────────────────────

interface GraphNode {
  id: number;
  kind: "decision" | "entity";
  label: string;
  entityType?: "technology" | "pattern";
  x: number;
  y: number;
  w: number;
  h: number;
}

interface GraphEdge {
  source: number;
  target: number;
  label?: string;
  dashed?: boolean;
}

interface CodeSnippet {
  text: string;
  /** X offset from center (600) */
  dx: number;
  /** Stagger delay within phase 2, in seconds */
  stagger: number;
}

// ── Node & edge data ────────────────────────────────────────────────

const NODES: GraphNode[] = [
  // Decisions (violet)
  { id: 0, kind: "decision", label: "Use PostgreSQL",  x: 340, y: 130, w: 160, h: 42 },
  { id: 1, kind: "decision", label: "Add Caching",     x: 700, y: 150, w: 140, h: 42 },
  // Entities
  { id: 2, kind: "entity", entityType: "technology", label: "PostgreSQL",    x: 200, y: 210, w: 110, h: 30 },
  { id: 3, kind: "entity", entityType: "technology", label: "Redis",         x: 830, y: 100, w: 80,  h: 30 },
  { id: 4, kind: "entity", entityType: "pattern",    label: "Async Pattern", x: 540, y: 220, w: 120, h: 30 },
];

const EDGES: GraphEdge[] = [
  { source: 0, target: 2, label: "INVOLVES" },
  { source: 0, target: 4, label: "INVOLVES" },
  { source: 1, target: 3, label: "INVOLVES" },
  { source: 1, target: 4, label: "DEPENDS_ON" },
  { source: 1, target: 0, label: "SUPERSEDES", dashed: true },
];

const CODE_SNIPPETS: CodeSnippet[] = [
  { text: 'def handle_migration():',          dx: -140, stagger: 0 },
  { text: 'db.execute("ALTER TABLE...")',      dx:  80,  stagger: 0.4 },
  { text: 'await claude.extract(log)',         dx: -60,  stagger: 0.8 },
  { text: 'graph.connect(nodes)',              dx:  160, stagger: 1.2 },
];

// ── Colour helpers ──────────────────────────────────────────────────

function entityFill(type?: string): string {
  switch (type) {
    case "technology": return "rgba(251,146,60,0.12)";
    case "pattern":    return "rgba(236,72,153,0.12)";
    default:           return "rgba(139,92,246,0.08)";
  }
}

function entityStroke(type?: string): string {
  switch (type) {
    case "technology": return "rgba(251,146,60,0.3)";
    case "pattern":    return "rgba(236,72,153,0.3)";
    default:           return "rgba(139,92,246,0.4)";
  }
}

function nodeAccentColor(node: GraphNode): string {
  if (node.kind === "decision") return "rgba(139,92,246,0.8)";
  switch (node.entityType) {
    case "technology": return "rgba(251,146,60,0.8)";
    case "pattern":    return "rgba(236,72,153,0.8)";
    default:           return "rgba(139,92,246,0.8)";
  }
}

// ── Geometry helpers ────────────────────────────────────────────────

function nodeCx(n: GraphNode): number { return n.x + n.w / 2; }
function nodeCy(n: GraphNode): number { return n.y + n.h / 2; }

function edgeLength(x1: number, y1: number, x2: number, y2: number): number {
  return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

function pseudoRandom(index: number): number {
  return ((index * 2654435761) % 97) / 97;
}

// ── Component ───────────────────────────────────────────────────────

export function HeroConductor() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="w-full" style={{ aspectRatio: "1200 / 800" }} />;
  }

  // Precompute edge geometry for gradients and rendering
  const edgeGeometry = EDGES.map((edge, i) => {
    const sNode = NODES[edge.source];
    const tNode = NODES[edge.target];
    const sx = nodeCx(sNode);
    const sy = nodeCy(sNode);
    const tx = nodeCx(tNode);
    const ty = nodeCy(tNode);
    const len = edgeLength(sx, sy, tx, ty);
    return { edge, i, sNode, tNode, sx, sy, tx, ty, len };
  });

  return (
    <div className="w-full" style={{ aspectRatio: "1200 / 800" }}>
      <svg
        viewBox="0 0 1200 800"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMax slice"
        className="w-full h-full"
        role="img"
        aria-label="Cinematic animation of a developer conducting code into a knowledge graph — code snippets float upward from a laptop and transform into connected decision and entity nodes"
      >
        {/* ── CSS keyframes & animation classes ──────────────── */}
        <style>{`
          /* ── Phase 1: Developer silhouette fade-in (0-2s) ── */
          @media (prefers-reduced-motion: no-preference) {
            .hc-dev-enter {
              opacity: 0;
              transform: translateY(30px);
              animation: hcDevIn 1.8s ease-out forwards;
            }
            @keyframes hcDevIn {
              to { opacity: 1; transform: translateY(0); }
            }

            .hc-laptop-glow {
              opacity: 0;
              animation: hcLaptopGlow 1.2s ease-out 0.6s forwards;
            }
            @keyframes hcLaptopGlow {
              to { opacity: 1; }
            }

            .hc-hand-glow {
              opacity: 0;
              animation: hcHandGlow 1s ease-out 1.2s forwards;
            }
            @keyframes hcHandGlow {
              to { opacity: 0.7; }
            }

            /* ── Phase 2: Code snippets float up (2-5s) ── */
            .hc-snippet {
              opacity: 0;
              animation: hcSnippetFloat 2.5s ease-out forwards;
            }
            @keyframes hcSnippetFloat {
              0%   { opacity: 0;   transform: translateY(0); }
              15%  { opacity: 0.8; transform: translateY(-40px); }
              70%  { opacity: 0.6; transform: translateY(-200px); }
              100% { opacity: 0;   transform: translateY(-250px); }
            }

            /* ── Phase 2: Light trails draw in (2-5s) ── */
            .hc-trail {
              opacity: 0;
              animation: hcTrailFadeIn 0.3s ease-out forwards;
            }
            @keyframes hcTrailFadeIn {
              to { opacity: 1; }
            }
            @keyframes hcTrailDraw {
              to { stroke-dashoffset: 0; }
            }

            /* ── Phase 3: Sparkle bursts (5-8s) ── */
            .hc-sparkle {
              opacity: 0;
              transform: scale(0);
              animation: hcSparkleBurst 0.8s ease-out forwards;
            }
            @keyframes hcSparkleBurst {
              0%   { opacity: 0;   transform: scale(0); }
              40%  { opacity: 1;   transform: scale(1.5); }
              100% { opacity: 0;   transform: scale(2); }
            }

            /* ── Phase 3: Graph nodes scale-in (5-8s) ── */
            .hc-node-enter {
              opacity: 0;
              transform: scale(0.3);
              animation: hcNodeIn 0.7s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
            }
            @keyframes hcNodeIn {
              to { opacity: 1; transform: scale(1); }
            }

            /* ── Phase 3: Graph edges draw-in (5-8s) ── */
            .hc-edge-enter {
              opacity: 0;
              animation: hcEdgeFadeIn 0.15s ease-out forwards;
            }
            @keyframes hcEdgeFadeIn {
              to { opacity: 1; }
            }
            @keyframes hcEdgeDrawLine {
              to { stroke-dashoffset: 0; }
            }

            /* ── Phase 4: Edge labels fade in (8-10s) ── */
            .hc-edge-label {
              opacity: 0;
              animation: hcLabelIn 0.5s ease-out forwards;
            }
            @keyframes hcLabelIn {
              to { opacity: 0.5; }
            }

            /* ── Idle animations (10s+) ── */
            .hc-idle-breathe {
              animation: hcBreathe 5s ease-in-out infinite;
            }
            @keyframes hcBreathe {
              0%, 100% { transform: scaleY(1); }
              50%      { transform: scaleY(1.008); }
            }

            .hc-idle-float {
              animation: hcFloat 4s ease-in-out infinite;
            }
            @keyframes hcFloat {
              0%, 100% { transform: translateY(0); }
              50%      { transform: translateY(-3px); }
            }

            .hc-idle-pulse {
              animation: hcPulse 3s ease-in-out infinite;
            }
            @keyframes hcPulse {
              0%, 100% { opacity: 0.3; }
              50%      { opacity: 0.5; }
            }

            .hc-idle-hand-pulse {
              animation: hcHandPulse 3.5s ease-in-out infinite;
            }
            @keyframes hcHandPulse {
              0%, 100% { opacity: 0.5; }
              50%      { opacity: 0.8; }
            }

            .hc-idle-trail-shimmer {
              animation: hcTrailShimmer 4s ease-in-out infinite;
            }
            @keyframes hcTrailShimmer {
              0%, 100% { opacity: 0.15; stroke-width: 1.5; }
              50%      { opacity: 0.35; stroke-width: 2.5; }
            }
          }

          /* ── Reduced motion ───────────────────────────── */
          @media (prefers-reduced-motion: reduce) {
            .hc-dev-enter,
            .hc-laptop-glow,
            .hc-hand-glow,
            .hc-node-enter,
            .hc-edge-enter,
            .hc-edge-label,
            .hc-trail,
            .hc-sparkle,
            .hc-idle-breathe,
            .hc-idle-float,
            .hc-idle-pulse,
            .hc-idle-hand-pulse,
            .hc-idle-trail-shimmer {
              animation: none !important;
            }
            .hc-dev-enter {
              opacity: 1 !important;
              transform: none !important;
            }
            .hc-laptop-glow {
              opacity: 1 !important;
            }
            .hc-hand-glow {
              opacity: 0.7 !important;
            }
            .hc-node-enter {
              opacity: 1 !important;
              transform: scale(1) !important;
            }
            .hc-edge-enter {
              opacity: 1 !important;
            }
            .hc-edge-enter line {
              stroke-dashoffset: 0 !important;
            }
            .hc-edge-label {
              opacity: 0.5 !important;
            }
            .hc-trail {
              opacity: 1 !important;
            }
            .hc-trail path {
              stroke-dashoffset: 0 !important;
            }
            .hc-idle-pulse {
              opacity: 0.4 !important;
            }
            .hc-idle-trail-shimmer {
              opacity: 0.25 !important;
            }
            /* Code snippets are transitional — hide in reduced motion */
            .hc-snippet {
              opacity: 0 !important;
            }
            /* Sparkles are transitional — hide in reduced motion */
            .hc-sparkle {
              opacity: 0 !important;
              transform: scale(0) !important;
            }
          }
        `}</style>

        {/* ── Gradient & filter defs ─────────────────────── */}
        <defs>
          {/* Laptop screen violet radial glow */}
          <radialGradient id="hc-screen-glow" cx="50%" cy="50%" r="60%">
            <stop offset="0%"   stopColor="rgba(139,92,246,0.35)" />
            <stop offset="60%"  stopColor="rgba(139,92,246,0.12)" />
            <stop offset="100%" stopColor="rgba(139,92,246,0)" />
          </radialGradient>

          {/* Hand glow radial gradients */}
          <radialGradient id="hc-hand-glow-l" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="rgba(139,92,246,0.4)" />
            <stop offset="100%" stopColor="rgba(139,92,246,0)" />
          </radialGradient>
          <radialGradient id="hc-hand-glow-r" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="rgba(139,92,246,0.4)" />
            <stop offset="100%" stopColor="rgba(139,92,246,0)" />
          </radialGradient>

          {/* Light trail gradient: violet -> rose -> orange */}
          <linearGradient id="hc-trail-grad-l" x1="450" y1="540" x2="300" y2="180" gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stopColor="rgba(139,92,246,0.8)" />
            <stop offset="50%"  stopColor="rgba(236,72,153,0.6)" />
            <stop offset="100%" stopColor="rgba(251,146,60,0.4)" />
          </linearGradient>
          <linearGradient id="hc-trail-grad-r" x1="750" y1="540" x2="900" y2="180" gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stopColor="rgba(139,92,246,0.8)" />
            <stop offset="50%"  stopColor="rgba(236,72,153,0.6)" />
            <stop offset="100%" stopColor="rgba(251,146,60,0.4)" />
          </linearGradient>

          {/* Edge gradients */}
          {edgeGeometry.map(({ i, sNode, tNode, sx, sy, tx, ty }) => (
            <linearGradient
              key={`hc-eg-${i}`}
              id={`hc-eg-${i}`}
              x1={sx}
              y1={sy}
              x2={tx}
              y2={ty}
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0%"   stopColor={nodeAccentColor(sNode)} />
              <stop offset="100%" stopColor={nodeAccentColor(tNode)} />
            </linearGradient>
          ))}

          {/* Bottom fade gradient */}
          <linearGradient id="hc-bottom-fade" x1="0" y1="720" x2="0" y2="800" gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stopColor="hsl(250,20%,6%)" stopOpacity="0" />
            <stop offset="100%" stopColor="hsl(250,20%,6%)" stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* ═══════════════════════════════════════════════════
            PHASE 1: Developer silhouette (0-2s)
            ═══════════════════════════════════════════════════ */}
        <g className="hc-dev-enter">
          {/* Idle breathing wrapper — transform-origin at base of torso */}
          <g
            className="hc-idle-breathe"
            style={{ transformOrigin: "600px 700px", animationDelay: "10s" }}
          >
            {/* ── Head: ellipse ── */}
            <ellipse
              cx={600}
              cy={490}
              rx={28}
              ry={32}
              fill="rgba(20,15,40,0.85)"
              stroke="rgba(139,92,246,0.14)"
              strokeWidth={1.2}
            />

            {/* ── Neck ── */}
            <rect
              x={591}
              y={520}
              width={18}
              height={16}
              fill="rgba(20,15,40,0.85)"
            />

            {/* ── Torso: geometric trapezoidal shape ── */}
            <path
              d="M 555 536 L 645 536 L 660 620 L 540 620 Z"
              fill="rgba(20,15,40,0.85)"
              stroke="rgba(139,92,246,0.13)"
              strokeWidth={1}
            />

            {/* ── Shoulders ── */}
            <path
              d="M 555 536 Q 520 536 490 550"
              fill="none"
              stroke="rgba(139,92,246,0.13)"
              strokeWidth={1.2}
            />
            <path
              d="M 645 536 Q 680 536 710 550"
              fill="none"
              stroke="rgba(139,92,246,0.13)"
              strokeWidth={1.2}
            />

            {/* ── Left arm: curved from shoulder up to hand ── */}
            <path
              d="M 490 550 Q 460 560 445 555 Q 430 548 440 538 Q 445 530 450 540"
              fill="none"
              stroke="rgba(20,15,40,0.85)"
              strokeWidth={8}
            />
            <path
              d="M 490 550 Q 460 560 445 555 Q 430 548 440 538 Q 445 530 450 540"
              fill="none"
              stroke="rgba(139,92,246,0.13)"
              strokeWidth={1.2}
            />

            {/* ── Right arm: curved from shoulder up to hand ── */}
            <path
              d="M 710 550 Q 740 560 755 555 Q 770 548 760 538 Q 755 530 750 540"
              fill="none"
              stroke="rgba(20,15,40,0.85)"
              strokeWidth={8}
            />
            <path
              d="M 710 550 Q 740 560 755 555 Q 770 548 760 538 Q 755 530 750 540"
              fill="none"
              stroke="rgba(139,92,246,0.13)"
              strokeWidth={1.2}
            />

            {/* ── Laptop base (angled) ── */}
            <path
              d="M 430 590 L 770 590 L 790 630 L 410 630 Z"
              fill="rgba(20,15,40,0.7)"
              stroke="rgba(139,92,246,0.12)"
              strokeWidth={0.8}
            />

            {/* ── Laptop screen (rectangle) ── */}
            <rect
              x={470}
              y={540}
              width={260}
              height={50}
              rx={3}
              fill="rgba(15,10,35,0.9)"
              stroke="rgba(139,92,246,0.2)"
              strokeWidth={1}
            />

            {/* ── Laptop screen glow ── */}
            <rect
              x={470}
              y={540}
              width={260}
              height={50}
              rx={3}
              fill="url(#hc-screen-glow)"
              className="hc-laptop-glow"
            />

            {/* ── Hand glow: left ── */}
            <circle
              cx={450}
              cy={540}
              r={30}
              fill="url(#hc-hand-glow-l)"
              className="hc-hand-glow"
            />
            {/* Idle hand glow pulse — left */}
            <circle
              cx={450}
              cy={540}
              r={30}
              fill="url(#hc-hand-glow-l)"
              className="hc-idle-hand-pulse"
              style={{ opacity: 0, animationDelay: "10.5s" }}
            />

            {/* ── Hand glow: right ── */}
            <circle
              cx={750}
              cy={540}
              r={30}
              fill="url(#hc-hand-glow-r)"
              className="hc-hand-glow"
            />
            {/* Idle hand glow pulse — right */}
            <circle
              cx={750}
              cy={540}
              r={30}
              fill="url(#hc-hand-glow-r)"
              className="hc-idle-hand-pulse"
              style={{ opacity: 0, animationDelay: "11s" }}
            />
          </g>
        </g>

        {/* ═══════════════════════════════════════════════════
            PHASE 2: Code snippets floating up (2-5s)
            ═══════════════════════════════════════════════════ */}
        {CODE_SNIPPETS.map((snippet, i) => (
          <text
            key={`snippet-${i}`}
            x={600 + snippet.dx}
            y={530}
            textAnchor="middle"
            fill="rgba(148,163,184,0.8)"
            fontSize={11}
            fontFamily="'JetBrains Mono', monospace"
            className="hc-snippet"
            style={{ animationDelay: `${2 + snippet.stagger}s` }}
          >
            {snippet.text}
          </text>
        ))}

        {/* ═══════════════════════════════════════════════════
            PHASE 2: Light trails from hands to graph area (2-5s)
            ═══════════════════════════════════════════════════ */}
        {/* Left trail: hand (450,540) curving up-left toward graph area */}
        <g className="hc-trail" style={{ animationDelay: "2.5s" }}>
          <path
            d="M 450 540 Q 400 400 340 280 Q 300 200 280 160"
            fill="none"
            stroke="url(#hc-trail-grad-l)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray="500"
            strokeDashoffset="500"
            style={{
              animation: "hcTrailDraw 2s ease-out 2.5s forwards",
            }}
          />
        </g>
        {/* Left trail idle shimmer */}
        <path
          d="M 450 540 Q 400 400 340 280 Q 300 200 280 160"
          fill="none"
          stroke="url(#hc-trail-grad-l)"
          strokeWidth={2}
          strokeLinecap="round"
          className="hc-idle-trail-shimmer"
          style={{ opacity: 0, animationDelay: "10s" }}
        />

        {/* Right trail: hand (750,540) curving up-right toward graph area */}
        <g className="hc-trail" style={{ animationDelay: "2.8s" }}>
          <path
            d="M 750 540 Q 800 400 860 280 Q 880 220 870 130"
            fill="none"
            stroke="url(#hc-trail-grad-r)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeDasharray="520"
            strokeDashoffset="520"
            style={{
              animation: "hcTrailDraw 2s ease-out 2.8s forwards",
            }}
          />
        </g>
        {/* Right trail idle shimmer */}
        <path
          d="M 750 540 Q 800 400 860 280 Q 880 220 870 130"
          fill="none"
          stroke="url(#hc-trail-grad-r)"
          strokeWidth={2}
          strokeLinecap="round"
          className="hc-idle-trail-shimmer"
          style={{ opacity: 0, animationDelay: "10.5s" }}
        />

        {/* ═══════════════════════════════════════════════════
            PHASE 3: Sparkle particles at node positions (5-8s)
            ═══════════════════════════════════════════════════ */}
        {NODES.map((node, i) => (
          <circle
            key={`sparkle-${i}`}
            cx={nodeCx(node)}
            cy={nodeCy(node)}
            r={4}
            fill={nodeAccentColor(node).replace("0.8)", "0.9)")}
            className="hc-sparkle"
            style={{
              animationDelay: `${5 + i * 0.35}s`,
              transformOrigin: `${nodeCx(node)}px ${nodeCy(node)}px`,
            }}
          />
        ))}

        {/* ═══════════════════════════════════════════════════
            PHASE 3: Graph edges draw-in (5-8s)
            ═══════════════════════════════════════════════════ */}
        {edgeGeometry.map(({ edge, i, sx, sy, tx, ty, len }) => {
          const delay = 5.8 + i * 0.3;
          const drawDuration = 0.6;
          const isSupersedesEdge = edge.dashed === true;
          const strokeRef = isSupersedesEdge
            ? "rgba(236,72,153,0.5)"
            : `url(#hc-eg-${i})`;

          const dashArray = isSupersedesEdge ? "6 3" : `${len}`;
          const dashedTotalLen = Math.ceil(len / 9) * 9;

          const mx = (sx + tx) / 2;
          const my = (sy + ty) / 2;

          return (
            <g key={`edge-${i}`}>
              {/* Draw-in line */}
              <g
                className="hc-edge-enter"
                style={{ animationDelay: `${delay}s` }}
              >
                <line
                  x1={sx}
                  y1={sy}
                  x2={tx}
                  y2={ty}
                  stroke={strokeRef}
                  strokeWidth={1}
                  strokeOpacity={0.4}
                  strokeDasharray={dashArray}
                  strokeDashoffset={isSupersedesEdge ? dashedTotalLen : len}
                  style={{
                    animation: `hcEdgeDrawLine ${drawDuration}s ease-out ${delay}s forwards`,
                  }}
                />
              </g>

              {/* Idle pulse overlay */}
              <line
                x1={sx}
                y1={sy}
                x2={tx}
                y2={ty}
                stroke={strokeRef}
                strokeWidth={1}
                strokeDasharray={isSupersedesEdge ? "6 3" : "none"}
                className="hc-idle-pulse"
                style={{
                  opacity: 0,
                  animationDelay: `${10 + pseudoRandom(i) * 2}s`,
                }}
              />

              {/* Phase 4: Edge label at midpoint (8-10s) */}
              {edge.label && (
                <text
                  x={mx}
                  y={my - 6}
                  textAnchor="middle"
                  fill="rgba(255,255,255,0.5)"
                  fontSize={8}
                  fontFamily="'Instrument Sans', sans-serif"
                  className="hc-edge-label"
                  style={{ animationDelay: `${8 + i * 0.25}s` }}
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* ═══════════════════════════════════════════════════
            PHASE 3: Graph nodes scale-in (5-8s)
            ═══════════════════════════════════════════════════ */}
        {NODES.map((node, i) => {
          const delay = 5.3 + i * 0.4;
          const idleDelay = 10 + pseudoRandom(node.id) * 3;
          const cx = nodeCx(node);
          const cy = nodeCy(node);

          if (node.kind === "decision") {
            return (
              <g
                key={`node-${node.id}`}
                className="hc-node-enter"
                style={{
                  animationDelay: `${delay}s`,
                  transformOrigin: `${cx}px ${cy}px`,
                }}
              >
                <g
                  className="hc-idle-float"
                  style={{ animationDelay: `${idleDelay}s` }}
                >
                  <rect
                    x={node.x}
                    y={node.y}
                    width={node.w}
                    height={node.h}
                    rx={12}
                    ry={12}
                    fill="rgba(139,92,246,0.08)"
                    stroke="rgba(139,92,246,0.4)"
                    strokeWidth={1.5}
                  />
                  <text
                    x={cx}
                    y={cy + 1}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill="rgba(255,255,255,0.9)"
                    fontSize={11}
                    fontFamily="'Instrument Sans', sans-serif"
                  >
                    {node.label}
                  </text>
                </g>
              </g>
            );
          }

          // Entity node — pill shape
          return (
            <g
              key={`node-${node.id}`}
              className="hc-node-enter"
              style={{
                animationDelay: `${delay}s`,
                transformOrigin: `${cx}px ${cy}px`,
              }}
            >
              <g
                className="hc-idle-float"
                style={{ animationDelay: `${idleDelay}s` }}
              >
                <rect
                  x={node.x}
                  y={node.y}
                  width={node.w}
                  height={node.h}
                  rx={16}
                  ry={16}
                  fill={entityFill(node.entityType)}
                  stroke={entityStroke(node.entityType)}
                  strokeWidth={1}
                />
                <text
                  x={cx}
                  y={cy + 1}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill="rgba(255,255,255,0.8)"
                  fontSize={10}
                  fontFamily="'Instrument Sans', sans-serif"
                >
                  {node.label}
                </text>
              </g>
            </g>
          );
        })}

        {/* ═══════════════════════════════════════════════════
            Bottom fade — blends into page background
            ═══════════════════════════════════════════════════ */}
        <rect
          x={0}
          y={720}
          width={1200}
          height={80}
          fill="url(#hc-bottom-fade)"
        />
      </svg>
    </div>
  );
}
