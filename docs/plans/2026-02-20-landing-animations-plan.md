# Landing Page Premium Animations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace generic GIF screenshots with 6 bespoke SVG/CSS animations that directly demonstrate what Continuum does — making the landing page feel like a premium product launch rather than a generic SaaS template.

**Architecture:** Each animation is a self-contained React component in `apps/web/components/landing/`. They use pure SVG + CSS animations orchestrated with `animation-delay` and the existing `useScrollAnimation` hook. No external animation libraries. The main page.tsx imports and places them, keeping GIFs as lazy-loaded fallbacks.

**Tech Stack:** React 19, SVG, CSS animations (keyframes), requestAnimationFrame for particles, existing Nebula design tokens

---

### Task 1: Hero Graph — Self-Assembling Knowledge Graph

The centerpiece animation. An SVG knowledge graph that builds itself in phases over ~8 seconds, then gently idles.

**Files:**
- Create: `apps/web/components/landing/hero-graph.tsx`

**Step 1: Create the component**

Create `apps/web/components/landing/hero-graph.tsx`. This is a complex SVG animation component. Here are the key specs for the implementer:

**Graph data:**
- 3 decision nodes (violet gradient border, rounded rectangles):
  - "Use PostgreSQL for relational data"
  - "Switch to async ORM"
  - "Add Redis caching layer"
- 5 entity nodes (colored circles/pills based on type):
  - "PostgreSQL" (orange, technology)
  - "SQLAlchemy" (orange, technology)
  - "Redis" (orange, technology)
  - "Async Pattern" (rose, pattern)
  - "Performance" (violet, concept)
- Edges between them (gradient strokes that draw in via stroke-dasharray animation):
  - Decision 1 → PostgreSQL, SQLAlchemy
  - Decision 2 → SQLAlchemy, Async Pattern
  - Decision 2 --SUPERSEDES--> Decision 1 (rose dashed edge)
  - Decision 3 → Redis, Performance
  - SQLAlchemy → Async Pattern (DEPENDS_ON)

**Animation phases (CSS animation-delay orchestration):**
- Phase 1 (0-2s): Decision 1 fades in at center with pulse-glow
- Phase 2 (2-4s): Entity nodes emerge from decision 1, edges draw in (stroke-dashoffset animates from full length to 0)
- Phase 3 (4-6s): Decision 2 appears, shared entity "SQLAlchemy" gets a second edge, SUPERSEDES edge draws
- Phase 4 (6-8s): Decision 3 and remaining entities appear
- Idle (8s+): All nodes have subtle `animate-float` with different delays. Edges have a flowing gradient pulse (a small bright spot that travels along the path using SVG `<animate>` or CSS).

**Node rendering:**
- Decision nodes: `<g>` containing `<rect rx="12">` with gradient fill (violet-500/10 fill, violet-500/40 stroke) + `<text>` label (white, 11px, Instrument Sans)
- Entity nodes: `<g>` containing `<rect rx="20">` (pill shape) with type-based colors (orange for tech, rose for pattern, violet for concept) + `<text>` label (10px)
- All nodes wrapped in a group with `opacity: 0` + CSS animation `fadeSlideIn` that triggers at the appropriate delay

**Edge rendering:**
- `<path>` elements with `stroke-dasharray` set to the path length and `stroke-dashoffset` animating from path-length to 0
- Gradient strokes using `<linearGradient>` (violet → rose for decision-decision, violet → entity-color for decision-entity)
- The SUPERSEDES edge should be dashed (stroke-dasharray: 4 2)

**SVG container:**
- viewBox: `0 0 800 500`
- Responsive: `width="100%" height="auto"` with `max-width: 900px`
- `aria-hidden="true"` (decorative)
- Respect `prefers-reduced-motion`: if reduced motion, show the final state immediately (all nodes/edges visible, no animation)

**Component interface:**
```tsx
export function HeroGraph() {
  // Uses useState for mounted check (hydration safety)
  // Returns SVG wrapped in a container div with relative positioning
  // The glow effect behind it is handled in page.tsx, not here
}
```

**CSS keyframes needed** (add to component via `<style>` JSX or inline styles):
- `fadeSlideIn`: `opacity 0 → 1, translateY 8px → 0` over 0.6s ease-out
- `drawEdge`: `stroke-dashoffset: [pathLength] → 0` over 1s ease-in-out
- `edgePulse`: A subtle opacity oscillation (0.6 → 1 → 0.6) over 3s infinite
- `nodeFloat`: `translateY(0) → translateY(-3px) → translateY(0)` over 4s ease-in-out infinite

**Step 2: Verify it builds**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 3: Commit**

```bash
git add apps/web/components/landing/hero-graph.tsx
git commit -m "feat: add self-assembling hero knowledge graph animation"
```

---

### Task 2: Pulsing Network — Feature 1 Animation

A compact animated graph for the "See the Connections" feature section.

**Files:**
- Create: `apps/web/components/landing/pulsing-network.tsx`

**Step 1: Create the component**

Specs:
- 6 nodes in a roughly circular/organic layout: 2 decision nodes (violet), 4 entity nodes (mixed colors)
- viewBox: `0 0 400 300`
- On scroll-enter (receives `isVisible` prop): nodes pop in with staggered `scale-in` (0, 100ms, 200ms, ...), then edges draw between them
- After initial animation: one node "highlights" (its stroke brightens, connected edges glow) — this cycles to a different node every 3 seconds to show graph traversal
- Idle: gentle float on all nodes, subtle edge pulse
- `prefers-reduced-motion`: show static final state

**Component interface:**
```tsx
export function PulsingNetwork({ isVisible }: { isVisible: boolean }) {
  // Renders SVG with nodes + edges
  // Uses isVisible to trigger entry animation
  // Uses setInterval for highlight cycling in idle state
}
```

**Step 2: Verify build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 3: Commit**

```bash
git add apps/web/components/landing/pulsing-network.tsx
git commit -m "feat: add pulsing network animation for knowledge graph feature"
```

---

### Task 3: Conversation Extraction — Feature 2 Animation

Animated chat-to-decision-trace for the "Capture What Matters" feature section.

**Files:**
- Create: `apps/web/components/landing/conversation-extract.tsx`

**Step 1: Create the component**

Specs:
- Two-column layout (use CSS grid or flex, NOT SVG for this one — it's DOM-based)
- **Left column (chat):**
  - 3 chat messages that appear sequentially on scroll-enter:
    1. Human (right-aligned, violet gradient bg): "We need to choose a database for user sessions"
    2. AI (left-aligned, glass bg): "Redis would be ideal — it supports TTL expiration natively and handles high-throughput reads well."
    3. Human: "Let's go with Redis. The TTL feature is the deciding factor."
  - Each message appears with `fadeSlideIn` + 1s delay between them
  - Typing indicator (three animated dots) shows briefly before each AI message

- **Right column (decision trace card):**
  - A glass-card styled container with 5 fields that fill in sequentially AFTER the conversation completes:
    1. **Trigger**: "Need session storage solution" (appears at ~4s)
    2. **Context**: "High-throughput reads required" (at ~4.8s)
    3. **Options**: "Redis, Memcached, PostgreSQL" (at ~5.6s)
    4. **Decision**: "Redis" (at ~6.4s, highlighted in violet)
    5. **Rationale**: "Native TTL expiration support" (at ~7.2s)
  - Each field fades in with a subtle violet glow flash
  - After all fields complete, a green checkmark appears and the card border glows violet

- Container: max-width 700px, centered within parent
- `prefers-reduced-motion`: show everything immediately
- `aria-hidden="true"` on the whole thing (decorative)

**Component interface:**
```tsx
export function ConversationExtract({ isVisible }: { isVisible: boolean }) {
  // DOM-based (not SVG)
  // Uses isVisible to trigger the sequence
  // CSS animations with animation-delay for orchestration
}
```

**Step 2: Verify build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 3: Commit**

```bash
git add apps/web/components/landing/conversation-extract.tsx
git commit -m "feat: add conversation extraction animation for capture feature"
```

---

### Task 4: File Scan — Feature 3 Animation

Animated file-tree-to-graph transformation for the "Zero-Effort Import" feature section.

**Files:**
- Create: `apps/web/components/landing/file-scan.tsx`

**Step 1: Create the component**

Specs:
- Two-phase animation within a single container (max-width 500px)

**Phase 1 — File tree (0-4s after visible):**
  - A mini file tree structure (DOM-based, monospace font):
    ```
    ~/.claude/projects/
    ├── continuum/
    │   ├── session-001.jsonl  ← scan line sweeps
    │   ├── session-002.jsonl  ← scan line sweeps
    │   └── session-003.jsonl  ← scan line sweeps
    ```
  - Files appear with staggered fade-in
  - A highlight "scan line" (violet gradient, 2px tall) sweeps left-to-right across each file name sequentially (1s per file)
  - As each file is scanned, its text color changes from slate-500 to slate-200

**Phase 2 — Extraction (4-8s):**
  - Small decision cards (pill-shaped, glass-styled) emerge from each scanned file and float upward
  - Cards read: "Use PostgreSQL", "Add caching", "Switch to TypeScript"
  - A counter in the corner ticks up: "3 decisions extracted → 7 → 12"
  - The cards shrink slightly and fade as they rise, suggesting they're flowing into the graph

- `prefers-reduced-motion`: show final state (tree + "12 decisions extracted")
- `aria-hidden="true"`

**Component interface:**
```tsx
export function FileScan({ isVisible }: { isVisible: boolean }) {
  // DOM-based animation
  // Uses isVisible prop + CSS animation-delay for orchestration
}
```

**Step 2: Verify build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 3: Commit**

```bash
git add apps/web/components/landing/file-scan.tsx
git commit -m "feat: add file scan animation for auto-import feature"
```

---

### Task 5: Step Micro-Animations — How It Works Icons

Small looping animations that replace the static lucide icons in the How It Works cards.

**Files:**
- Create: `apps/web/components/landing/step-animations.tsx`

**Step 1: Create the component**

Export 4 small animated SVG components (each 40x40px viewBox):

**ChatAnimation** (Step 1: Code with AI):
- Two chat bubbles that alternate. First bubble slides in from left (human), pauses, then second slides in from right (AI). Loop.
- Typing dots (3 circles that scale up/down sequentially) appear before each bubble

**ScanAnimation** (Step 2: Extract):
- A rectangle representing a document with 4 horizontal lines (text)
- A highlight bar sweeps top-to-bottom across the lines repeatedly
- Lines that have been "scanned" briefly flash violet before returning to normal

**MergeAnimation** (Step 3: Resolve):
- Two small circles (both labeled "PG" or just colored the same) start separated
- They slide together, merge into one circle (scale animation), and a checkmark appears
- Loop: split apart, slide together, merge

**GraphAnimation** (Step 4: Visualize):
- 4 tiny dots arranged in a diamond
- Edges draw between them one by one (stroke-dasharray animation)
- After all edges drawn, brief pause, then fade out and restart

All animations:
- 40x40 SVG viewBox, rendered at the icon size
- Loop infinitely
- Activated by `isVisible` prop (don't animate until scrolled into view)
- `prefers-reduced-motion`: show static icon (no animation)
- Each animation is ~3-4s per loop

**Component interface:**
```tsx
export function ChatAnimation({ isVisible }: { isVisible: boolean }) { ... }
export function ScanAnimation({ isVisible }: { isVisible: boolean }) { ... }
export function MergeAnimation({ isVisible }: { isVisible: boolean }) { ... }
export function GraphAnimation({ isVisible }: { isVisible: boolean }) { ... }
```

**Step 2: Verify build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 3: Commit**

```bash
git add apps/web/components/landing/step-animations.tsx
git commit -m "feat: add micro-animations for how-it-works step icons"
```

---

### Task 6: Ambient Particles

Floating particle layer that adds depth between sections.

**Files:**
- Create: `apps/web/components/landing/ambient-particles.tsx`

**Step 1: Create the component**

Specs:
- Fixed-position `<canvas>` element covering the full viewport, behind content (z-index: 1)
- ~25 particles, each a small glowing dot (2-4px radius)
- Colors: randomly picked from violet (rgba(139,92,246,0.3)), rose (rgba(236,72,153,0.2)), orange (rgba(251,146,60,0.2))
- Movement: slow drift (0.1-0.3px per frame) in random directions, wrapping around edges
- Parallax: particles move slightly based on scroll position (multiply scrollY by 0.02-0.05 factor)
- Draw using `canvas.getContext("2d")`, requestAnimationFrame loop
- Clean up animation frame on unmount
- `prefers-reduced-motion`: render particles but don't animate them (static dots)
- Canvas is `aria-hidden="true"` and `pointer-events: none`
- Resize handling: update canvas dimensions on window resize

**Component interface:**
```tsx
export function AmbientParticles() {
  // Renders a fixed-position canvas
  // Uses useRef for canvas, useEffect for animation loop
  // Returns just the canvas element
}
```

**Step 2: Verify build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 3: Commit**

```bash
git add apps/web/components/landing/ambient-particles.tsx
git commit -m "feat: add ambient floating particle layer"
```

---

### Task 7: Integrate All Animations into Landing Page

Wire all 6 animation components into `apps/web/app/page.tsx`.

**Files:**
- Modify: `apps/web/app/page.tsx`

**Step 1: Add imports**

At the top of page.tsx, add:
```tsx
import { HeroGraph } from "@/components/landing/hero-graph"
import { PulsingNetwork } from "@/components/landing/pulsing-network"
import { ConversationExtract } from "@/components/landing/conversation-extract"
import { FileScan } from "@/components/landing/file-scan"
import { ChatAnimation, ScanAnimation, MergeAnimation, GraphAnimation } from "@/components/landing/step-animations"
import { AmbientParticles } from "@/components/landing/ambient-particles"
```

**Step 2: Add AmbientParticles to the page**

Right after `<div className="nebula-bg" .../>`, add:
```tsx
{mounted && <AmbientParticles />}
```

**Step 3: Replace hero GIF with HeroGraph**

In the hero section, replace the GIF container (the `<div className="relative mx-auto max-w-5xl">` block containing the `<img>` tag) with:

```tsx
<div className="relative mx-auto max-w-5xl">
  <div
    className="absolute -inset-4 bg-gradient-to-r from-violet-500/20 via-fuchsia-500/10 to-orange-500/20 rounded-3xl blur-2xl opacity-60"
    aria-hidden="true"
  />
  <div className="relative rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.5)] bg-[hsl(250,20%,4%)] p-8">
    <HeroGraph />
  </div>
</div>
```

**Step 4: Update FeatureSection to accept an animation prop**

Modify the `FeatureSection` component to accept an optional `animation` ReactNode. When provided, render the animation above the GIF (animation is primary, GIF lazy-loads below as supplementary):

```tsx
function FeatureSection({
  title,
  description,
  imageSrc,
  imageAlt,
  glowColor,
  imagePosition,
  animation,
}: {
  title: string
  description: string
  imageSrc: string
  imageAlt: string
  glowColor: keyof typeof glowColors
  imagePosition: "left" | "right"
  animation?: React.ReactNode
}) {
  const { ref, isVisible } = useScrollAnimation()

  const textBlock = ( /* ...same as before... */ )

  const imageBlock = (
    <div className="relative">
      <div
        className={`absolute -inset-4 bg-gradient-to-br ${glowColors[glowColor]} rounded-3xl blur-2xl`}
        aria-hidden="true"
      />
      <div className="relative space-y-4">
        {/* Custom animation (primary) */}
        {animation && (
          <div className="rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.4)] bg-[hsl(250,20%,4%)] p-6">
            {React.cloneElement(animation as React.ReactElement, { isVisible })}
          </div>
        )}
        {/* GIF fallback (lazy-loaded supplement) */}
        <div className="rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.4)]">
          <img src={imageSrc} alt={imageAlt} className="w-full h-auto" loading="lazy" />
        </div>
      </div>
    </div>
  )

  return ( /* ...same grid layout as before... */ )
}
```

**Step 5: Pass animations to FeatureSection instances**

Update the three FeatureSection calls:

```tsx
<FeatureSection
  title="See the Connections"
  description="..."
  imageSrc="/media/knowledge-graph.gif"
  imageAlt="..."
  glowColor="violet"
  imagePosition="right"
  animation={<PulsingNetwork isVisible={false} />}
/>

<FeatureSection
  title="Capture What Matters"
  description="..."
  imageSrc="/media/capture-session.gif"
  imageAlt="..."
  glowColor="rose"
  imagePosition="left"
  animation={<ConversationExtract isVisible={false} />}
/>

<FeatureSection
  title="Zero-Effort Import"
  description="..."
  imageSrc="/media/import-logs.gif"
  imageAlt="..."
  glowColor="orange"
  imagePosition="right"
  animation={<FileScan isVisible={false} />}
/>
```

Note: `isVisible={false}` is passed initially; the FeatureSection will clone the element and pass the real `isVisible` value.

**Step 6: Update HowItWorks to use step animations**

Replace the static lucide icon in each step card with the corresponding animation component. Map step index to animation:

```tsx
const stepAnimations = [ChatAnimation, ScanAnimation, MergeAnimation, GraphAnimation]

// In the step card, replace:
// <step.icon className="w-5 h-5 text-violet-400" />
// With:
const StepAnim = stepAnimations[i]
// ...
<StepAnim isVisible={isVisible} />
```

Keep the step.icon as a fallback or remove it since the animation replaces it.

**Step 7: Verify build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 8: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: integrate all premium animations into landing page"
```

---

### Task 8: Final Typecheck, Lint, Build

**Files:**
- Any files with issues

**Step 1: Typecheck**

Run: `cd /Users/shehral/continuum/apps/web && pnpm typecheck 2>&1 | tail -20`

Fix any type errors.

**Step 2: Lint**

Run: `cd /Users/shehral/continuum/apps/web && pnpm lint 2>&1 | tail -20`

Fix any NEW lint errors (ignore pre-existing ones in other files).

**Step 3: Build**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -30`

Ensure build succeeds.

**Step 4: Commit fixes (if any)**

```bash
git add -A
git commit -m "fix: resolve typecheck and lint issues for landing animations"
```

---

## Summary

| Task | Component | Type | Complexity |
|------|-----------|------|------------|
| 1 | Hero Graph | SVG animation | High — 8-10 nodes, phased entry, idle state |
| 2 | Pulsing Network | SVG animation | Medium — 6 nodes, highlight cycling |
| 3 | Conversation Extract | DOM animation | Medium — chat bubbles + decision trace card |
| 4 | File Scan | DOM animation | Medium — file tree + extraction flow |
| 5 | Step Micro-Animations | SVG animations | Medium — 4 small looping animations |
| 6 | Ambient Particles | Canvas | Low — simple particle system |
| 7 | Integration | Page modification | Medium — wire everything together |
| 8 | Polish | Build verification | Low — fix any issues |

**Dependencies:** Tasks 1-6 are independent (can be built in any order). Task 7 depends on all of 1-6. Task 8 depends on 7.
