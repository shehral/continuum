# Hero Conductor Animation Design

**Date**: 2026-02-20
**Branch**: `feature/landing-page`
**Goal**: Replace the self-assembling HeroGraph with a cinematic full-bleed developer conductor scene that shows code transforming into a knowledge graph.

## Context

The current hero section has a self-assembling SVG knowledge graph inside a glass card. While technically impressive, it doesn't tell the product story. The HackerRank-inspired conductor animation creates a cinematic hero where a developer silhouette orchestrates code-to-graph transformation — visually telling the entire Continuum value proposition in one scene.

## Scene Layout

The hero section is a full `100vh` viewport. The SVG canvas covers the entire area as a background layer. Headline text floats above in the upper third, the conductor scene fills the lower two-thirds.

```
┌─────────────────────────────────────────────────┐
│  [nav bar - transparent]                        │
│                                                 │
│         * Knowledge Graph for AI Decisions      │  eyebrow badge
│                                                 │
│         Your AI Decisions, Remembered.           │  headline (z-10, above SVG)
│         Captures engineering decisions...         │  subheadline
│                                                 │
│     ╭─Decision─╮    ╭─Entity─╮                  │  graph nodes (phase 3)
│     │Use Postgres│───│PostgreSQL│                │  rising from code lines
│     ╰──────────╯    ╰────────╯                  │
│           ↑              ↑                      │
│      light trails between code and nodes         │
│     [code lines floating up & transforming]      │  phase 2
│           ↑              ↑                      │
│    ┌──────────────────────────┐                  │
│    │  def handle_migration(): │  code text       │  phase 1
│    │    db.execute(query)     │  floating up     │
│    └──────────────────────────┘                  │
│              \    /                              │
│               \  /   light trails from hands     │
│            ┌──────┐                             │
│            │ dev  │  developer silhouette        │
│            │figure│  at laptop                  │
│            ├──────┴───────┐                     │
│            │   laptop     │                     │
│            └──────────────┘                     │
│  gradient fade to background                     │
└─────────────────────────────────────────────────┘
```

## The Developer Silhouette

A stylized upper-body SVG silhouette (head, shoulders, arms) seated at a minimal laptop outline. Minimalist/geometric — not photorealistic. Faces the viewer, arms slightly raised from the keyboard as if conjuring.

- Fill: `rgba(20,15,40,0.8)` (dark, blends with background)
- Edge glow: subtle violet stroke on shoulders/head outline
- Laptop: simple rectangular outline with glowing screen

## Animation Phases (~10 seconds total, then idle)

### Phase 1 (0-2s): The Developer Appears

- Silhouette fades in from bottom with subtle slide-up
- Laptop screen emits a soft violet glow
- Ambient light around hands begins to pulse

### Phase 2 (2-5s): Code Rises

- 3-4 code snippet text elements float upward from the laptop screen
- Lines: `"def handle_migration():"`, `"db.execute(ALTER TABLE...)"`, `"await claude.extract(log)"`, `"graph.connect(nodes)"`
- Each snippet is monospace text (JetBrains Mono) in slate-400 with subtle glow
- Drift upward with slight lateral spread, opacity fading as they rise
- Light trails (gradient strokes) follow each code line from the developer's hands

### Phase 3 (5-8s): Transformation

- Code snippets reach mid-height, blur/dissolve
- Decision/entity nodes materialize in their place (scale-in + glow):
  - "Use PostgreSQL" (violet decision pill)
  - "PostgreSQL" (orange entity pill)
  - "Add Caching" (violet decision pill)
  - "Redis" (orange entity pill)
  - "Async Pattern" (rose pattern pill)
- Gradient edges draw between connected nodes (stroke-dasharray animation)
- Sparkle particles burst at each transformation point

### Phase 4 (8-10s): Graph Settles

- Nodes drift into final positions
- Edges finish drawing
- "INVOLVES" and "SUPERSEDES" labels fade in on edges
- Full graph floats gently (idle state begins)

### Idle State

- Developer silhouette has subtle breathing animation (very slight scale)
- Laptop glow pulses gently
- Graph nodes float slowly
- Occasional spark particles travel along edges
- Light trails between hands and graph shimmer

## Light Effects

- **Hand glow**: Radial gradient centered on each hand, violet to transparent
- **Light trails**: Curved `<path>` elements from hands to code/nodes, animated with stroke-dasharray (flowing gradient)
- **Sparkle particles**: Small circles that travel along paths at transformation moments
- **Laptop screen glow**: Soft violet rectangle glow emanating from the laptop

## Technical Approach

- **File**: `apps/web/components/landing/hero-conductor.tsx`
- **viewBox**: `"0 0 1200 800"` — wide format, scales responsively
- Pure SVG + CSS keyframes, no JS animation loop
- `prefers-reduced-motion`: shows final state immediately (developer + graph, no animation)
- `role="img"` with `aria-label` for accessibility
- Self-contained React component, same pattern as existing landing animations

## Changes to page.tsx

- Remove `HeroGraph` import and usage
- Import new `HeroConductor` component
- Hero section restructured: SVG is `absolute inset-0`, text content is `relative z-10`
- Keep eyebrow badge, headline, subheadline — positioned in upper portion
- Remove "Scroll to explore" indicator (the scene draws the eye downward)
- Keep nebula background blobs (they complement the scene)

## File Structure

```
apps/web/components/landing/
├── hero-conductor.tsx     — NEW: Developer conductor scene (replaces hero-graph)
├── hero-graph.tsx         — KEEP: unused by page, can be deleted later
├── pulsing-network.tsx    — Feature 1 mini-graph (unchanged)
├── conversation-extract.tsx — Feature 2 chat-to-trace (unchanged)
├── file-scan.tsx          — Feature 3 import animation (unchanged)
├── step-animations.tsx    — How It Works micro-animations (unchanged)
└── ambient-particles.tsx  — Floating particle layer (unchanged)
```
