# Landing Page Premium Animations Design

**Date**: 2026-02-20
**Branch**: `feature/landing-page`
**Goal**: Replace generic scroll-fade animations with bespoke, product-specific animations that demonstrate what Continuum does.

## Context

The current landing page has scroll-triggered fade/slide animations and static GIF screenshots. These work but feel generic. The animations below make every section feel alive and directly showcase the product's value. GIFs are kept as lazy-loaded fallbacks below each custom animation.

## Animation Inventory

### 1. Hero — Self-Assembling Knowledge Graph

Full-width SVG canvas below the headline. Builds a knowledge graph from nothing over ~8 seconds, then idles.

**Phases:**
- Phase 1 (0-2s): Single DecisionTrace node fades in at center with pulse-glow
- Phase 2 (2-4s): Entity nodes emerge (PostgreSQL, Relational Data, SQLAlchemy) connected by gradient edges that draw themselves via stroke-dasharray animation
- Phase 3 (4-6s): Second decision appears, shared entities connect both decisions, SUPERSEDES edge draws between decisions
- Phase 4 (6-8s): Third cluster appears, more connections form. ~8-10 nodes, ~12 edges total.
- Idle: Nodes float gently, edges have flowing gradient pulse, occasional spark particles travel along edges

**Tech:** Pure SVG + CSS animations. Nodes are `<g>` groups. Edges are `<path>` with stroke-dasharray/dashoffset. Orchestrated with CSS animation-delay. No external libraries.

**Size:** ~300x400px responsive container, scales with viewport.

### 2. Feature 1 — Pulsing Network Graph

Compact animated graph (~6 nodes) for the Knowledge Graph feature section.

- Nodes pop in with staggered scale-in
- Edges draw between them
- One node highlights, connections illuminate (graph traversal demo)
- Idle: gentle float + edge pulse

### 3. Feature 2 — Conversation Extraction

Animated chat-to-decision-trace sequence for AI Capture feature.

**Left column:** Chat bubbles appear sequentially (human → AI → human) with typing indicator between
**Right column:** Decision Trace card builds field by field (Trigger → Context → Options → Decision → Rationale) with glow on each completion. Final checkmark + violet glow.

### 4. Feature 3 — File Scan Animation

File-tree-to-graph transformation for Auto Import feature.

- Mini file tree (3-4 .jsonl files) appears
- Scan line sweeps across each file
- Decision cards extract from files and float upward
- Cards shrink into graph nodes that connect
- Counter: "3 decisions... 7 decisions... 12 decisions"

### 5. How It Works — Step Micro-Animations

Small looping animations (40x40px) inside each step card's icon area:

| Step | Animation |
|------|-----------|
| Code with AI | Two chat bubbles alternating with typing dots |
| Extract | Document with highlight sweep scanning text lines |
| Resolve | Two duplicate nodes merge into one |
| Visualize | Tiny 4-node graph drawing edges |

Activate on scroll-enter, loop infinitely.

### 6. Ambient Particles

Fixed-position layer with ~20-30 floating particles (violet, rose, orange dots). Drift with subtle parallax on scroll. Implemented with requestAnimationFrame, no libraries.

## Technical Approach

- All animations are pure SVG + CSS + vanilla JS (requestAnimationFrame)
- No animation libraries (no Framer Motion, no GSAP, no Lottie)
- Each animation is a self-contained React component
- Animations trigger on scroll via the existing useScrollAnimation hook
- Performance: will-change hints, transform-only animations, reduced motion media query support
- Accessibility: All animations respect prefers-reduced-motion, decorative elements have aria-hidden

## File Structure

```
apps/web/components/landing/
├── hero-graph.tsx          — Self-assembling knowledge graph
├── pulsing-network.tsx     — Feature 1 mini-graph
├── conversation-extract.tsx — Feature 2 chat-to-trace
├── file-scan.tsx           — Feature 3 import animation
├── step-animations.tsx     — How It Works micro-animations
└── ambient-particles.tsx   — Floating particle layer
```

## GIF Handling

Existing GIFs are kept as lazy-loaded images below each custom animation as "real product" proof. They load after the custom animations, not replacing them.
