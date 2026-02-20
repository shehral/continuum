# Landing Page Design

**Date**: 2026-02-20
**Branch**: `feature/landing-page`
**Approach**: Cinematic Scroll (single-page, scroll-driven, full-viewport sections)

## Context

Continuum has no public-facing landing page. The root route goes directly to an authenticated dashboard. This design adds a showcase page for general audiences and investors — pure visual impact, no specific CTA.

**Audience**: General public, investors, non-technical stakeholders
**Goal**: Impress visitors with the product's quality and vision
**Vibe**: Premium / futuristic (Linear, Vercel, Arc Browser aesthetic)
**Design system**: Leverages existing Nebula theme (glassmorphism, violet/rose/orange gradients, Instrument Sans)

## Page Architecture

```
apps/web/app/(public)/layout.tsx    → Public layout (no sidebar, no auth)
apps/web/app/(public)/page.tsx      → Landing page
```

Uses Next.js route groups so the landing page has its own minimal layout while authenticated routes remain protected under the existing AppShell layout.

**Public nav**: Logo + "Continuum" wordmark left, "Sign In" ghost button right. Transparent background, blurs on scroll.

## Sections

### 1. Hero (100vh)

**Background**: Dark canvas with animated Nebula orbs (violet, rose, orange blurred circles drifting). Radial gradient from center fading to edges.

**Content** (centered, stacked):
- **Eyebrow badge**: Small glass pill — "Knowledge Graph for AI Decisions"
- **Headline**: "Your AI Decisions," (white) + "Remembered." (gradient text: violet → rose → orange)
- **Subheadline**: "Continuum captures the engineering decisions hidden in your AI coding sessions and transforms them into a searchable knowledge graph."
- **Product screenshot**: Dashboard/graph GIF in a glass card with glowing violet border, slight perspective tilt, soft reflection. Animates with slide-in-up + scale-in.

### 2. Feature Highlights (3 sections)

Three full-width alternating sections. Each has text on one side and a product GIF in a glass card on the other. Animate on scroll via Intersection Observer.

**Feature 1 — Knowledge Graph** (text left, GIF right)
- Heading: "See the Connections" (gradient text)
- Body: "Every decision creates a ripple. Continuum maps how your technology choices, design patterns, and architectural decisions interconnect — revealing relationships you never noticed."
- Accent: Violet glow, floating entity-type badges
- GIF: `knowledge-graph.gif`

**Feature 2 — AI-Guided Capture** (GIF left, text right)
- Heading: "Capture What Matters" (gradient text)
- Body: "An AI interviewer guides you through structured decision capture — extracting the trigger, context, options, and rationale behind every choice. No more lost tribal knowledge."
- Accent: Rose glow, chat-bubble decorative elements
- GIF: `capture-session.gif`

**Feature 3 — Automated Extraction** (text left, GIF right)
- Heading: "Zero-Effort Import" (gradient text)
- Body: "Point Continuum at your Claude Code conversation logs and watch as decisions are automatically extracted, entities are resolved, and your knowledge graph grows — all without lifting a finger."
- Accent: Orange glow, progress-bar animation
- GIF: `import-logs.gif`

### 3. How It Works

Horizontal step-by-step pipeline (collapses to vertical on mobile). Four numbered glass cards connected by animated gradient lines (violet → rose → orange).

| Step | Icon | Title | Description |
|------|------|-------|-------------|
| 01 | MessageSquare | Code with AI | Have conversations with Claude Code, Copilot, or any AI assistant while building software |
| 02 | Scan | Extract | Continuum parses your conversation logs and uses AI to identify decisions, entities, and rationale |
| 03 | GitBranch | Resolve | A 7-stage entity resolution pipeline deduplicates and canonicalizes every technology, pattern, and concept |
| 04 | Network | Visualize | Explore your decisions as an interactive knowledge graph — search, filter, and discover connections |

Lines animate left-to-right on scroll. Cards fade in with staggered delays. Gradient line pulses subtly.

### 4. Tech Stack & Credibility

Dark glass card with stats grid + tech logo strip.

**Stats** (counter animation on scroll):
- `838+` automated tests
- `7-stage` entity resolution
- `2,048` embedding vectors
- `3` specialized databases

**Tech strip**: Monochrome logos brightening on hover — Next.js, React, FastAPI, PostgreSQL, Neo4j, Redis, NVIDIA, Docker, Kubernetes.

### 5. Footer

Minimal:
- Continuum logo + wordmark (gradient)
- Tagline: "Transforming ephemeral AI collaboration into structured knowledge."
- Links: Contact email, Sign In
- Copyright: "© 2026 Ali Shehral"

## Technical Decisions

- **Scroll animations**: Intersection Observer API (no heavy animation library)
- **Counter animation**: requestAnimationFrame-based number ticker
- **GIF handling**: Existing media assets, lazy-loaded with loading="lazy"
- **Responsive**: Mobile-first with Tailwind breakpoints, pipeline collapses to vertical
- **Performance**: No new dependencies beyond what exists in the project
- **Reuse**: Button (ghost, gradient variants), Card (glass variant), Badge, existing animations from globals.css
