# Hero Conductor Animation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the HeroGraph with a cinematic full-bleed developer conductor scene that shows code transforming into a knowledge graph.

**Architecture:** A single self-contained React component (`HeroConductor`) renders a full SVG scene with a developer silhouette, floating code snippets, and graph nodes. The SVG is positioned as an absolute background layer in the hero section. All animation is CSS keyframes — no JS animation loops. The existing `page.tsx` hero section is restructured to overlay text on top of the SVG.

**Tech Stack:** React, SVG, CSS keyframes, TypeScript

---

### Task 1: Create the HeroConductor SVG component

**Files:**
- Create: `apps/web/components/landing/hero-conductor.tsx`

**Context:** This is the main animation component. It renders a `1200x800` viewBox SVG containing:
1. A developer silhouette (head, shoulders, arms, laptop)
2. Code snippets that float upward from the laptop
3. Decision/entity graph nodes that materialize from the code
4. Edges connecting the graph nodes
5. Light trail effects from the developer's hands
6. Sparkle particles at transformation points

The animation plays over ~10 seconds in 4 phases, then idles. Follow the exact same patterns used in the existing `hero-graph.tsx` component (in the same directory): hydration guard with `useState(false)` + `useEffect`, CSS keyframes inside `<style>` tags within the SVG, `prefers-reduced-motion` media queries, `role="img"` + `aria-label`.

**Step 1: Create the component file with data layer and helpers**

Create `apps/web/components/landing/hero-conductor.tsx` with the following structure. The component should be `"use client"` and export `HeroConductor`.

```tsx
"use client";

import { useState, useEffect } from "react";

// ── Data ─────────────────────────────────────────────────────────────

interface CodeSnippet {
  id: number;
  text: string;
  /** X offset from center of laptop screen */
  xOffset: number;
  /** Phase 2 stagger delay in seconds */
  delay: number;
}

interface GraphNode {
  id: number;
  kind: "decision" | "entity";
  label: string;
  entityType?: "technology" | "pattern" | "concept";
  /** Final x position in SVG coordinates */
  x: number;
  /** Final y position */
  y: number;
  w: number;
  h: number;
  /** Phase 3 stagger delay in seconds */
  delay: number;
}

interface GraphEdge {
  source: number;
  target: number;
  label?: string;
  dashed?: boolean;
  /** Phase 3 stagger delay in seconds */
  delay: number;
}

const CODE_SNIPPETS: CodeSnippet[] = [
  { id: 0, text: "def handle_migration():", xOffset: -120, delay: 0 },
  { id: 1, text: 'db.execute("ALTER TABLE...")', xOffset: 60, delay: 0.4 },
  { id: 2, text: "await claude.extract(log)", xOffset: -40, delay: 0.8 },
  { id: 3, text: "graph.connect(nodes)", xOffset: 100, delay: 1.2 },
];

const GRAPH_NODES: GraphNode[] = [
  // Decisions
  { id: 0, kind: "decision", label: "Use PostgreSQL", x: 340, y: 120, w: 160, h: 38, delay: 0 },
  { id: 1, kind: "decision", label: "Add Caching", x: 700, y: 150, w: 140, h: 38, delay: 0.4 },
  // Entities
  { id: 2, kind: "entity", entityType: "technology", label: "PostgreSQL", x: 260, y: 220, w: 104, h: 30, delay: 0.2 },
  { id: 3, kind: "entity", entityType: "technology", label: "Redis", x: 820, y: 230, w: 72, h: 30, delay: 0.6 },
  { id: 4, kind: "entity", entityType: "pattern", label: "Async Pattern", x: 540, y: 100, w: 120, h: 30, delay: 0.8 },
];

const GRAPH_EDGES: GraphEdge[] = [
  { source: 0, target: 2, label: "INVOLVES", delay: 0.3 },
  { source: 0, target: 4, label: "INVOLVES", delay: 0.6 },
  { source: 1, target: 3, label: "INVOLVES", delay: 0.7 },
  { source: 1, target: 0, label: "SUPERSEDES", dashed: true, delay: 1.0 },
  { source: 4, target: 3, label: "DEPENDS_ON", delay: 1.2 },
];

// ── Colour helpers (same palette as hero-graph.tsx) ──────────────────

function entityFill(type?: string): string {
  switch (type) {
    case "technology": return "rgba(251,146,60,0.12)";
    case "pattern":    return "rgba(236,72,153,0.12)";
    case "concept":    return "rgba(139,92,246,0.12)";
    default:           return "rgba(139,92,246,0.08)";
  }
}

function entityStroke(type?: string): string {
  switch (type) {
    case "technology": return "rgba(251,146,60,0.3)";
    case "pattern":    return "rgba(236,72,153,0.3)";
    case "concept":    return "rgba(139,92,246,0.3)";
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

function nodeCx(n: GraphNode): number { return n.x + n.w / 2; }
function nodeCy(n: GraphNode): number { return n.y + n.h / 2; }

function edgeLength(x1: number, y1: number, x2: number, y2: number): number {
  return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

function pseudoRandom(index: number): number {
  return ((index * 2654435761) % 97) / 97;
}
```

**Step 2: Add the SVG developer silhouette paths**

Below the helpers, add the silhouette path data. This is a stylized upper-body developer at a laptop. The figure is centered at x=600, sitting at the bottom of the viewBox.

```tsx
// ── Developer silhouette path data ───────────────────────────────────
// Centered at x=600, bottom of viewport. Stylized geometric silhouette.

// Head: oval
const HEAD_CX = 600;
const HEAD_CY = 540;
const HEAD_RX = 28;
const HEAD_RY = 32;

// Shoulders/torso: trapezoid path from neck down to below viewport
const TORSO_PATH = "M 560,572 Q 555,590 530,620 L 530,800 L 670,800 L 670,620 Q 645,590 640,572 Z";

// Left arm: raised slightly, hand open as if conjuring
const LEFT_ARM_PATH = "M 555,590 Q 520,600 480,570 Q 460,555 450,540";
// Right arm: raised slightly, mirror
const RIGHT_ARM_PATH = "M 645,590 Q 680,600 720,570 Q 740,555 750,540";

// Left hand: small circle for glow anchor
const LEFT_HAND = { cx: 448, cy: 538 };
// Right hand
const RIGHT_HAND = { cx: 752, cy: 538 };

// Laptop body
const LAPTOP_BASE_PATH = "M 520,680 L 480,720 L 720,720 L 680,680 Z";
// Laptop screen
const LAPTOP_SCREEN_PATH = "M 530,620 L 530,680 L 670,680 L 670,620 Z";
```

**Step 3: Add the CSS keyframes inside the component**

Add the `<style>` block that defines all animation keyframes. Phase timing:
- Phase 1 (0-2s): Developer appears
- Phase 2 (2-5s): Code rises from laptop
- Phase 3 (5-8s): Code transforms into graph nodes + edges draw
- Phase 4 (8-10s): Graph settles, idle begins

```tsx
// ── Phase timing constants ───────────────────────────────────────────
const PHASE_1_START = 0;      // Developer appears
const PHASE_2_START = 2;      // Code rises
const PHASE_3_START = 5;      // Transformation
const PHASE_4_START = 8;      // Settle + idle
const IDLE_START = 10;        // Full idle

// ── CSS keyframes string ─────────────────────────────────────────────
const KEYFRAMES = `
  @media (prefers-reduced-motion: no-preference) {
    /* Phase 1: Developer silhouette fades in from below */
    .hc-dev-enter {
      opacity: 0;
      transform: translateY(30px);
      animation: hcDevIn 1.2s ease-out forwards;
    }
    @keyframes hcDevIn {
      to { opacity: 1; transform: translateY(0); }
    }

    /* Laptop screen glow pulse */
    .hc-laptop-glow {
      opacity: 0;
      animation: hcLaptopGlow 2s ease-out ${PHASE_1_START + 0.5}s forwards;
    }
    @keyframes hcLaptopGlow {
      0% { opacity: 0; }
      100% { opacity: 0.6; }
    }

    /* Hand glow appears after developer */
    .hc-hand-glow {
      opacity: 0;
      animation: hcHandGlowIn 1s ease-out ${PHASE_1_START + 1}s forwards,
                 hcHandPulse 3s ease-in-out ${IDLE_START}s infinite;
    }
    @keyframes hcHandGlowIn {
      to { opacity: 0.5; }
    }
    @keyframes hcHandPulse {
      0%, 100% { opacity: 0.4; }
      50% { opacity: 0.6; }
    }

    /* Phase 2: Code snippets float upward */
    .hc-code-rise {
      opacity: 0;
      animation: hcCodeRise 3s ease-out forwards;
    }
    @keyframes hcCodeRise {
      0% { opacity: 0; transform: translateY(0); }
      20% { opacity: 0.8; }
      70% { opacity: 0.6; }
      100% { opacity: 0; transform: translateY(-250px); }
    }

    /* Light trails from hands follow code upward */
    .hc-trail {
      opacity: 0;
      animation: hcTrailIn 0.5s ease-out forwards;
    }
    @keyframes hcTrailIn {
      to { opacity: 1; }
    }
    @keyframes hcTrailDraw {
      to { stroke-dashoffset: 0; }
    }

    /* Phase 3: Graph nodes materialize */
    .hc-node-enter {
      opacity: 0;
      transform: scale(0.3);
      animation: hcNodeIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
    }
    @keyframes hcNodeIn {
      to { opacity: 1; transform: scale(1); }
    }

    /* Sparkle burst at transformation */
    .hc-sparkle {
      opacity: 0;
      animation: hcSparkle 0.8s ease-out forwards;
    }
    @keyframes hcSparkle {
      0% { opacity: 0; transform: scale(0); }
      40% { opacity: 1; transform: scale(1.5); }
      100% { opacity: 0; transform: scale(2); }
    }

    /* Edge draw-in */
    @keyframes hcDrawEdge {
      to { stroke-dashoffset: 0; }
    }

    /* Edge labels fade in */
    .hc-edge-label {
      opacity: 0;
      animation: hcLabelIn 0.4s ease-out forwards;
    }
    @keyframes hcLabelIn {
      to { opacity: 0.5; }
    }

    /* Idle: gentle float */
    .hc-idle-float {
      animation: hcFloat 4s ease-in-out infinite;
    }
    @keyframes hcFloat {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-3px); }
    }

    /* Idle: edge pulse */
    .hc-idle-pulse {
      animation: hcEdgePulse 3s ease-in-out infinite;
    }
    @keyframes hcEdgePulse {
      0%, 100% { opacity: 0.3; }
      50% { opacity: 0.5; }
    }

    /* Idle: developer subtle breathing */
    .hc-dev-breathe {
      animation: hcBreathe 4s ease-in-out infinite;
    }
    @keyframes hcBreathe {
      0%, 100% { transform: scaleY(1); }
      50% { transform: scaleY(1.008); }
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .hc-dev-enter,
    .hc-hand-glow,
    .hc-laptop-glow,
    .hc-node-enter,
    .hc-trail,
    .hc-edge-label,
    .hc-idle-float,
    .hc-idle-pulse,
    .hc-dev-breathe {
      animation: none !important;
    }
    .hc-dev-enter { opacity: 1 !important; transform: none !important; }
    .hc-hand-glow { opacity: 0.5 !important; }
    .hc-laptop-glow { opacity: 0.6 !important; }
    .hc-node-enter { opacity: 1 !important; transform: none !important; }
    .hc-trail { opacity: 0.3 !important; }
    .hc-edge-label { opacity: 0.5 !important; }
    .hc-code-rise { animation: none !important; opacity: 0 !important; }
    .hc-sparkle { animation: none !important; opacity: 0 !important; }
    .hc-idle-pulse { opacity: 0.4 !important; }
  }
`;
```

**Step 4: Add the main component render function**

```tsx
export function HeroConductor() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="w-full h-full" />;
  }

  return (
    <svg
      viewBox="0 0 1200 800"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-full"
      role="img"
      aria-label="Animated scene of a developer orchestrating code that transforms into a knowledge graph"
      preserveAspectRatio="xMidYMax slice"
    >
      <style>{KEYFRAMES}</style>

      {/* ── Gradient defs ──────────────────────────────────── */}
      <defs>
        {/* Radial glow for hands */}
        <radialGradient id="hc-hand-glow-l" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(139,92,246,0.4)" />
          <stop offset="100%" stopColor="rgba(139,92,246,0)" />
        </radialGradient>
        <radialGradient id="hc-hand-glow-r" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(139,92,246,0.4)" />
          <stop offset="100%" stopColor="rgba(139,92,246,0)" />
        </radialGradient>

        {/* Laptop screen glow */}
        <radialGradient id="hc-screen-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(139,92,246,0.3)" />
          <stop offset="100%" stopColor="rgba(139,92,246,0)" />
        </radialGradient>

        {/* Bottom fade so the silhouette blends into page background */}
        <linearGradient id="hc-bottom-fade" x1="0" y1="0.7" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(0,0,0,0)" />
          <stop offset="100%" stopColor="hsl(250,20%,6%)" />
        </linearGradient>

        {/* Edge gradients */}
        {GRAPH_EDGES.map((edge, i) => {
          const sNode = GRAPH_NODES[edge.source];
          const tNode = GRAPH_NODES[edge.target];
          return (
            <linearGradient
              key={`hc-eg-${i}`}
              id={`hc-eg-${i}`}
              x1={nodeCx(sNode)}
              y1={nodeCy(sNode)}
              x2={nodeCx(tNode)}
              y2={nodeCy(tNode)}
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0%" stopColor={nodeAccentColor(sNode)} />
              <stop offset="100%" stopColor={nodeAccentColor(tNode)} />
            </linearGradient>
          );
        })}

        {/* Light trail gradient */}
        <linearGradient id="hc-trail-grad" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="rgba(139,92,246,0.5)" />
          <stop offset="50%" stopColor="rgba(236,72,153,0.3)" />
          <stop offset="100%" stopColor="rgba(251,146,60,0.1)" />
        </linearGradient>
      </defs>

      {/* ── Bottom fade overlay ────────────────────────────── */}
      <rect x="0" y="560" width="1200" height="240" fill="url(#hc-bottom-fade)" />

      {/* ── Developer silhouette (Phase 1) ─────────────────── */}
      <g className="hc-dev-enter" style={{ animationDelay: `${PHASE_1_START}s` }}>
        <g className="hc-dev-breathe" style={{ transformOrigin: "600px 650px", animationDelay: `${IDLE_START}s` }}>
          {/* Head */}
          <ellipse
            cx={HEAD_CX}
            cy={HEAD_CY}
            rx={HEAD_RX}
            ry={HEAD_RY}
            fill="rgba(20,15,40,0.85)"
            stroke="rgba(139,92,246,0.15)"
            strokeWidth={1}
          />
          {/* Torso */}
          <path
            d={TORSO_PATH}
            fill="rgba(20,15,40,0.85)"
            stroke="rgba(139,92,246,0.1)"
            strokeWidth={1}
          />
          {/* Left arm */}
          <path
            d={LEFT_ARM_PATH}
            fill="none"
            stroke="rgba(20,15,40,0.85)"
            strokeWidth={14}
            strokeLinecap="round"
          />
          <path
            d={LEFT_ARM_PATH}
            fill="none"
            stroke="rgba(139,92,246,0.12)"
            strokeWidth={1}
            strokeLinecap="round"
          />
          {/* Right arm */}
          <path
            d={RIGHT_ARM_PATH}
            fill="none"
            stroke="rgba(20,15,40,0.85)"
            strokeWidth={14}
            strokeLinecap="round"
          />
          <path
            d={RIGHT_ARM_PATH}
            fill="none"
            stroke="rgba(139,92,246,0.12)"
            strokeWidth={1}
            strokeLinecap="round"
          />

          {/* Laptop */}
          <path d={LAPTOP_SCREEN_PATH} fill="rgba(15,10,35,0.9)" stroke="rgba(139,92,246,0.2)" strokeWidth={1} />
          <path d={LAPTOP_BASE_PATH} fill="rgba(20,15,40,0.9)" stroke="rgba(139,92,246,0.15)" strokeWidth={1} />

          {/* Laptop screen glow */}
          <rect
            x={510}
            y={600}
            width={180}
            height={80}
            fill="url(#hc-screen-glow)"
            className="hc-laptop-glow"
          />
        </g>

        {/* Hand glows */}
        <circle
          cx={LEFT_HAND.cx}
          cy={LEFT_HAND.cy}
          r={40}
          fill="url(#hc-hand-glow-l)"
          className="hc-hand-glow"
        />
        <circle
          cx={RIGHT_HAND.cx}
          cy={RIGHT_HAND.cy}
          r={40}
          fill="url(#hc-hand-glow-r)"
          className="hc-hand-glow"
        />
      </g>

      {/* ── Light trails from hands (Phase 2) ──────────────── */}
      {[LEFT_HAND, RIGHT_HAND].map((hand, hi) => {
        const trailDelay = PHASE_2_START + hi * 0.3;
        // Curved path from hand up toward the graph area
        const endX = hand.cx + (hi === 0 ? 80 : -80);
        const endY = 280;
        const cpX = hand.cx + (hi === 0 ? 40 : -40);
        const cpY = 400;
        const d = `M ${hand.cx},${hand.cy} Q ${cpX},${cpY} ${endX},${endY}`;
        const len = 300; // approximate

        return (
          <g key={`trail-${hi}`}>
            <path
              d={d}
              fill="none"
              stroke="url(#hc-trail-grad)"
              strokeWidth={2}
              strokeDasharray={len}
              strokeDashoffset={len}
              className="hc-trail"
              style={{
                animationDelay: `${trailDelay}s`,
                animation: `hcTrailIn 0.5s ease-out ${trailDelay}s forwards, hcTrailDraw 1.5s ease-out ${trailDelay}s forwards`,
                strokeDasharray: len,
                strokeDashoffset: len,
              }}
            />
            {/* Shimmer overlay for idle */}
            <path
              d={d}
              fill="none"
              stroke="rgba(139,92,246,0.15)"
              strokeWidth={1.5}
              className="hc-idle-pulse"
              style={{ animationDelay: `${IDLE_START + hi}s`, opacity: 0 }}
            />
          </g>
        );
      })}

      {/* ── Code snippets floating up (Phase 2) ────────────── */}
      {CODE_SNIPPETS.map((snippet) => {
        const startX = 600 + snippet.xOffset;
        const startY = 580; // just above laptop screen
        const codeDelay = PHASE_2_START + snippet.delay;

        return (
          <text
            key={`code-${snippet.id}`}
            x={startX}
            y={startY}
            textAnchor="middle"
            fill="rgba(148,163,184,0.8)"
            fontSize={11}
            fontFamily="'JetBrains Mono', monospace"
            className="hc-code-rise"
            style={{ animationDelay: `${codeDelay}s` }}
          >
            {snippet.text}
          </text>
        );
      })}

      {/* ── Sparkle particles at transformation (Phase 3) ──── */}
      {GRAPH_NODES.map((node, i) => {
        const sparkleDelay = PHASE_3_START + node.delay;
        return (
          <circle
            key={`sparkle-${i}`}
            cx={nodeCx(node)}
            cy={nodeCy(node)}
            r={3}
            fill="rgba(139,92,246,0.8)"
            className="hc-sparkle"
            style={{ animationDelay: `${sparkleDelay}s`, transformOrigin: `${nodeCx(node)}px ${nodeCy(node)}px` }}
          />
        );
      })}

      {/* ── Graph edges (Phase 3) ──────────────────────────── */}
      {GRAPH_EDGES.map((edge, i) => {
        const sNode = GRAPH_NODES[edge.source];
        const tNode = GRAPH_NODES[edge.target];
        const sx = nodeCx(sNode);
        const sy = nodeCy(sNode);
        const tx = nodeCx(tNode);
        const ty = nodeCy(tNode);
        const len = edgeLength(sx, sy, tx, ty);
        const delay = PHASE_3_START + edge.delay + 0.3; // edges draw slightly after nodes
        const isSup = edge.dashed === true;
        const strokeRef = isSup ? "rgba(236,72,153,0.5)" : `url(#hc-eg-${i})`;
        const dashArray = isSup ? "6 3" : `${len}`;
        const offsetLen = isSup ? Math.ceil(len / 9) * 9 : len;
        const mx = (sx + tx) / 2;
        const my = (sy + ty) / 2;

        return (
          <g key={`edge-${i}`}>
            <line
              x1={sx} y1={sy} x2={tx} y2={ty}
              stroke={strokeRef}
              strokeWidth={1}
              strokeOpacity={0.4}
              strokeDasharray={dashArray}
              strokeDashoffset={offsetLen}
              style={{ animation: `hcDrawEdge 0.6s ease-out ${delay}s forwards` }}
            />
            {/* Idle pulse overlay */}
            <line
              x1={sx} y1={sy} x2={tx} y2={ty}
              stroke={strokeRef}
              strokeWidth={1}
              strokeDasharray={isSup ? "6 3" : "none"}
              className="hc-idle-pulse"
              style={{ opacity: 0, animationDelay: `${IDLE_START + pseudoRandom(i) * 2}s` }}
            />
            {/* Edge label */}
            {edge.label && (
              <text
                x={mx} y={my - 6}
                textAnchor="middle"
                fill="rgba(255,255,255,0.5)"
                fontSize={8}
                fontFamily="'Instrument Sans', sans-serif"
                className="hc-edge-label"
                style={{ animationDelay: `${delay + 0.3}s` }}
              >
                {edge.label}
              </text>
            )}
          </g>
        );
      })}

      {/* ── Graph nodes (Phase 3) ──────────────────────────── */}
      {GRAPH_NODES.map((node) => {
        const delay = PHASE_3_START + node.delay;
        const idleDelay = IDLE_START + pseudoRandom(node.id) * 3;

        const isDecision = node.kind === "decision";
        const rx = isDecision ? 12 : 16;
        const fill = isDecision ? "rgba(139,92,246,0.08)" : entityFill(node.entityType);
        const stroke = isDecision ? "rgba(139,92,246,0.4)" : entityStroke(node.entityType);
        const strokeW = isDecision ? 1.5 : 1;
        const textFill = isDecision ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.8)";
        const fontSize = isDecision ? 11 : 10;

        return (
          <g
            key={`node-${node.id}`}
            className="hc-node-enter"
            style={{ animationDelay: `${delay}s`, transformOrigin: `${nodeCx(node)}px ${nodeCy(node)}px` }}
          >
            <g className="hc-idle-float" style={{ animationDelay: `${idleDelay}s` }}>
              <rect
                x={node.x} y={node.y}
                width={node.w} height={node.h}
                rx={rx} ry={rx}
                fill={fill} stroke={stroke} strokeWidth={strokeW}
              />
              <text
                x={nodeCx(node)} y={nodeCy(node) + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill={textFill}
                fontSize={fontSize}
                fontFamily="'Instrument Sans', sans-serif"
              >
                {node.label}
              </text>
            </g>
          </g>
        );
      })}
    </svg>
  );
}
```

**Step 5: Verify the component compiles**

Run: `cd /Users/shehral/continuum && pnpm --filter web exec tsc --noEmit 2>&1 | head -20`

Expected: No errors in `hero-conductor.tsx`. (Pre-existing errors in other files are OK.)

**Step 6: Commit**

```bash
git add apps/web/components/landing/hero-conductor.tsx
git commit -m "feat: add hero conductor animation component"
```

---

### Task 2: Integrate HeroConductor into the landing page

**Files:**
- Modify: `apps/web/app/page.tsx:1-12` (imports)
- Modify: `apps/web/app/page.tsx:356-401` (hero section)

**Context:** Replace the HeroGraph glass card in the hero section with HeroConductor as a full-bleed background SVG. The text content (eyebrow badge, headline, subheadline) stays but is repositioned to the upper portion with `z-10` to float above the SVG. Remove the "Scroll to explore" indicator. Keep the nebula background blobs.

**Step 1: Update imports**

In `apps/web/app/page.tsx`, change the import line:

```tsx
// REMOVE this line:
import { HeroGraph } from "@/components/landing/hero-graph"

// ADD this line:
import { HeroConductor } from "@/components/landing/hero-conductor"
```

**Step 2: Replace the hero section**

Replace the entire `{/* Hero */}` section (lines 356-401) with:

```tsx
      {/* Hero */}
      <section className="relative min-h-screen flex flex-col items-center px-6 pt-16 overflow-hidden">
        {/* Nebula background blobs */}
        {mounted && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
            <div className="absolute top-1/4 left-[16%] w-72 h-72 bg-violet-500/12 rounded-full blur-3xl animate-float" />
            <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-fuchsia-500/8 rounded-full blur-3xl animate-float [animation-delay:-1.5s]" />
            <div className="absolute top-1/2 right-[16%] w-56 h-56 bg-orange-500/6 rounded-full blur-3xl animate-float [animation-delay:-3s]" />
          </div>
        )}

        {/* Conductor SVG - full bleed background */}
        {mounted && (
          <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
            <HeroConductor />
          </div>
        )}

        {/* Text overlay - positioned in upper portion */}
        <div className="relative z-10 max-w-4xl mx-auto text-center pt-16 sm:pt-24 animate-in fade-in slide-in-from-bottom-8 duration-1000">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] backdrop-blur-sm mb-8">
            <Sparkles className="w-3.5 h-3.5 text-violet-400" />
            <span className="text-xs font-medium text-slate-300">
              Knowledge Graph for AI Decisions
            </span>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
            Your AI Decisions,{" "}
            <span className="gradient-text">Remembered.</span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Continuum captures the engineering decisions hidden in your AI coding
            sessions and transforms them into a searchable knowledge graph.
          </p>
        </div>
      </section>
```

Key changes:
- Hero section: `justify-center` removed (text now top-aligned with padding)
- HeroConductor: `absolute inset-0`, fills the entire hero viewport
- Glass card wrapper: removed entirely
- "Scroll to explore" indicator: removed
- Text: `pt-16 sm:pt-24` instead of vertical centering, `mb-12` removed from subheadline

**Step 3: Verify typecheck and lint**

Run: `cd /Users/shehral/continuum && pnpm --filter web exec tsc --noEmit 2>&1 | head -20`
Run: `cd /Users/shehral/continuum && pnpm --filter web exec next lint 2>&1 | tail -20`

Expected: No new errors. The unused `HeroGraph` import should be gone.

**Step 4: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: replace HeroGraph with cinematic conductor scene in hero section"
```

---

### Task 3: Final verification — typecheck, lint, build

**Files:**
- None (verification only)

**Step 1: Run TypeScript typecheck**

Run: `cd /Users/shehral/continuum && pnpm --filter web exec tsc --noEmit 2>&1 | head -30`

Expected: No errors from `hero-conductor.tsx` or `page.tsx`. Pre-existing errors elsewhere are acceptable.

**Step 2: Run ESLint**

Run: `cd /Users/shehral/continuum && pnpm --filter web exec next lint 2>&1 | tail -30`

Expected: No new errors. Warnings about `no-img-element` on existing `<img>` tags are acceptable.

**Step 3: Run Next.js production build**

Run: `cd /Users/shehral/continuum && pnpm --filter web build 2>&1 | tail -30`

Expected: Build succeeds. The landing page route `/` should compile without errors.

**Step 4: Visual verification**

Start dev server if not running: `cd /Users/shehral/continuum && pnpm dev:web`

Open `http://localhost:3000` and verify:
1. Developer silhouette fades in from bottom center
2. Code snippets float upward from laptop
3. Light trails connect hands to rising code
4. Code transforms into graph nodes with sparkle effects
5. Edges draw between nodes
6. Idle state: gentle float, edge pulse, hand glow pulse
7. Headline text is readable above the scene
8. Mobile responsive (try narrow viewport)
