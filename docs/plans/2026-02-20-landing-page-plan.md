# Landing Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a cinematic scroll-driven landing page that showcases Continuum to general audiences and investors with maximum visual impact.

**Architecture:** New public route group `(public)` with its own minimal layout (no sidebar/auth). The existing middleware must be updated to exclude the landing page from auth protection. The page is a single client component with Intersection Observer for scroll-triggered animations, reusing the Nebula design system.

**Tech Stack:** Next.js 16 App Router, React 19, TailwindCSS 4, lucide-react, existing Nebula design tokens from globals.css

---

### Task 1: Update Middleware to Allow Public Landing Page

**Files:**
- Modify: `apps/web/middleware.ts`

**Step 1: Update the middleware matcher**

The current middleware protects all routes except `/login`, `/register`, and API routes. We need to also exclude the root `/` path so the landing page is publicly accessible.

Replace the entire file:

```typescript
import { auth } from "./auth"
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const publicPaths = ["/login", "/register"]

async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Landing page is public
  if (pathname === "/") {
    return NextResponse.next()
  }

  // Other public paths
  if (publicPaths.some((path) => pathname.startsWith(path))) {
    return NextResponse.next()
  }

  // Everything else requires auth
  return (auth as any)(request)
}

export default middleware

export const config = {
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|media).*)",
  ],
}
```

**Step 2: Verify the middleware compiles**

Run: `cd /Users/shehral/continuum/apps/web && npx tsc --noEmit middleware.ts 2>&1 | head -20`

Note: This may show module resolution warnings in isolation — that's fine. The real test is the dev server.

**Step 3: Commit**

```bash
git add apps/web/middleware.ts
git commit -m "feat: allow public access to landing page route"
```

---

### Task 2: Move Dashboard to /dashboard Route

The current `app/page.tsx` is the authenticated dashboard at `/`. We need to move it to `/dashboard` so `/` can serve the landing page.

**Files:**
- Move: `apps/web/app/page.tsx` → `apps/web/app/dashboard/page.tsx`

**Step 1: Create the dashboard directory and move the file**

```bash
mkdir -p /Users/shehral/continuum/apps/web/app/dashboard
mv /Users/shehral/continuum/apps/web/app/page.tsx /Users/shehral/continuum/apps/web/app/dashboard/page.tsx
```

**Step 2: Update any internal links pointing to `/`**

Search the codebase for links pointing to `"/"` that should now point to `"/dashboard"`. Key files to check:

- `apps/web/components/layout/sidebar.tsx` — the logo/home link
- `apps/web/app/login/page.tsx` — the callbackUrl default
- Any `<Link href="/">` references

For each file found, replace `href="/"` with `href="/dashboard"` where it refers to the authenticated dashboard (NOT the landing page).

Also update the login page's default callbackUrl:
```typescript
// In apps/web/app/login/page.tsx, change:
const callbackUrl = searchParams.get("callbackUrl") || "/"
// To:
const callbackUrl = searchParams.get("callbackUrl") || "/dashboard"
```

**Step 3: Update middleware to protect /dashboard**

The `/dashboard` route should still require auth. The middleware already protects everything not explicitly excluded, so `/dashboard` is already protected. No change needed.

**Step 4: Verify nothing is broken**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -30`

If there are import errors or broken links, fix them before proceeding.

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: move dashboard from / to /dashboard"
```

---

### Task 3: Create the Landing Page Shell

**Files:**
- Create: `apps/web/app/page.tsx` (new landing page)

**Step 1: Create the landing page file**

This is the main page component. It will be a `"use client"` component with scroll-triggered animations. Start with just the shell — nav, hero placeholder, and footer:

```tsx
"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import Link from "next/link"
import { GitBranch, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"

function useScrollAnimation() {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          observer.unobserve(el)
        }
      },
      { threshold: 0.15 }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return { ref, isVisible }
}

function useCountUp(target: number, isVisible: boolean, duration = 2000) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!isVisible) return

    const start = performance.now()
    function tick(now: number) {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.floor(eased * target))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [isVisible, target, duration])

  return count
}

export default function LandingPage() {
  const [mounted, setMounted] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    setMounted(true)
    const handleScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <div className="min-h-screen bg-[hsl(250,20%,6%)] text-white overflow-x-hidden">
      {/* Nebula background */}
      <div className="nebula-bg" aria-hidden="true" />

      {/* Navigation */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-[hsl(250,20%,6%)]/80 backdrop-blur-xl border-b border-white/[0.06]"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 border border-violet-500/30 flex items-center justify-center">
              <GitBranch className="w-4 h-4 text-violet-400" />
            </div>
            <span className="text-lg font-bold gradient-text">Continuum</span>
          </Link>
          <Link href="/login">
            <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white">
              Sign In
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      {/* (Task 4) */}

      {/* Features */}
      {/* (Task 5) */}

      {/* How It Works */}
      {/* (Task 6) */}

      {/* Tech & Credibility */}
      {/* (Task 7) */}

      {/* Footer */}
      <footer className="border-t border-white/[0.06] py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col items-center gap-4 text-center">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 border border-violet-500/30 flex items-center justify-center">
              <GitBranch className="w-3 h-3 text-violet-400" />
            </div>
            <span className="font-semibold gradient-text">Continuum</span>
          </div>
          <p className="text-sm text-slate-500 max-w-md">
            Transforming ephemeral AI collaboration into structured knowledge.
          </p>
          <div className="flex items-center gap-6 text-sm text-slate-500">
            <a href="mailto:shehral.m@northeastern.edu" className="hover:text-violet-400 transition-colors">
              Contact
            </a>
            <Link href="/login" className="hover:text-violet-400 transition-colors">
              Sign In
            </Link>
          </div>
          <p className="text-xs text-slate-600 mt-4">© 2026 Ali Shehral</p>
        </div>
      </footer>
    </div>
  )
}
```

**Step 2: Verify it renders**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

Expected: Build succeeds. The landing page at `/` should show the nav bar and footer.

**Step 3: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: add landing page shell with nav and footer"
```

---

### Task 4: Build the Hero Section

**Files:**
- Modify: `apps/web/app/page.tsx`

**Step 1: Replace the `{/* Hero */}` comment with the hero section**

Insert after the `</nav>` and before `{/* Features */}`:

```tsx
{/* Hero */}
<section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-16">
  {/* Floating orbs */}
  {mounted && (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      <div className="absolute top-1/4 left-1/6 w-72 h-72 bg-violet-500/12 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-fuchsia-500/8 rounded-full blur-3xl animate-float [animation-delay:-1.5s]" />
      <div className="absolute top-1/2 right-1/6 w-56 h-56 bg-orange-500/6 rounded-full blur-3xl animate-float [animation-delay:-3s]" />
    </div>
  )}

  {/* Content */}
  <div className="relative z-10 max-w-4xl mx-auto text-center animate-in fade-in slide-in-from-bottom-8 duration-1000">
    {/* Eyebrow badge */}
    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] backdrop-blur-sm mb-8">
      <Sparkles className="w-3.5 h-3.5 text-violet-400" />
      <span className="text-xs font-medium text-slate-300">Knowledge Graph for AI Decisions</span>
    </div>

    {/* Headline */}
    <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
      Your AI Decisions,{" "}
      <span className="gradient-text">Remembered.</span>
    </h1>

    {/* Subheadline */}
    <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed">
      Continuum captures the engineering decisions hidden in your AI coding sessions
      and transforms them into a searchable knowledge graph.
    </p>

    {/* Product showcase */}
    <div className="relative mx-auto max-w-5xl">
      {/* Glow behind the image */}
      <div className="absolute -inset-4 bg-gradient-to-r from-violet-500/20 via-fuchsia-500/10 to-orange-500/20 rounded-3xl blur-2xl opacity-60" aria-hidden="true" />

      {/* Screenshot container */}
      <div className="relative rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.5)]">
        <img
          src="/media/dashboard-trace.gif"
          alt="Continuum dashboard showing decision traces and analytics"
          className="w-full h-auto"
          loading="eager"
        />
        {/* Subtle gradient overlay at bottom for fade effect */}
        <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-[hsl(250,20%,6%)] to-transparent" aria-hidden="true" />
      </div>
    </div>
  </div>

  {/* Scroll indicator */}
  <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-pulse-glow">
    <span className="text-xs text-slate-500">Scroll to explore</span>
    <div className="w-5 h-8 rounded-full border border-white/20 flex items-start justify-center p-1">
      <div className="w-1 h-2 rounded-full bg-violet-400 animate-slide-in-down" />
    </div>
  </div>
</section>
```

**Step 2: Copy media assets to public directory**

The GIFs are in `/Users/shehral/continuum/media/`. Next.js serves files from `apps/web/public/`. We need to make them accessible:

```bash
mkdir -p /Users/shehral/continuum/apps/web/public/media
# Symlink instead of copying (GIFs are very large)
ln -sf /Users/shehral/continuum/media/dashboard-trace.gif /Users/shehral/continuum/apps/web/public/media/dashboard-trace.gif
ln -sf /Users/shehral/continuum/media/knowledge-graph.gif /Users/shehral/continuum/apps/web/public/media/knowledge-graph.gif
ln -sf /Users/shehral/continuum/media/capture-session.gif /Users/shehral/continuum/apps/web/public/media/capture-session.gif
ln -sf /Users/shehral/continuum/media/import-logs.gif /Users/shehral/continuum/apps/web/public/media/import-logs.gif
```

If symlinks don't work with Next.js dev server, fall back to copying:
```bash
cp /Users/shehral/continuum/media/dashboard-trace.gif /Users/shehral/continuum/apps/web/public/media/
cp /Users/shehral/continuum/media/capture-session.gif /Users/shehral/continuum/apps/web/public/media/
cp /Users/shehral/continuum/media/import-logs.gif /Users/shehral/continuum/apps/web/public/media/
cp /Users/shehral/continuum/media/knowledge-graph.gif /Users/shehral/continuum/apps/web/public/media/
```

Note: These GIFs are very large (20-378 MB). For production, they should be converted to optimized video formats (WebM/MP4). For now, we use GIFs for the prototype.

**Step 3: Verify**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: add hero section with animated orbs and product showcase"
```

---

### Task 5: Build the Feature Highlights Section

**Files:**
- Modify: `apps/web/app/page.tsx`

**Step 1: Replace the `{/* Features */}` comment**

Insert after the hero `</section>` and before `{/* How It Works */}`:

```tsx
{/* Features */}
<section className="relative py-32">
  {/* Feature 1: Knowledge Graph */}
  <FeatureSection
    useScrollAnimation={useScrollAnimation}
    title="See the Connections"
    description="Every decision creates a ripple. Continuum maps how your technology choices, design patterns, and architectural decisions interconnect — revealing relationships you never noticed."
    imageSrc="/media/knowledge-graph.gif"
    imageAlt="Interactive knowledge graph visualization showing decision and entity nodes"
    glowColor="violet"
    imagePosition="right"
  />

  {/* Feature 2: AI-Guided Capture */}
  <FeatureSection
    useScrollAnimation={useScrollAnimation}
    title="Capture What Matters"
    description="An AI interviewer guides you through structured decision capture — extracting the trigger, context, options, and rationale behind every choice. No more lost tribal knowledge."
    imageSrc="/media/capture-session.gif"
    imageAlt="AI-guided interview session capturing engineering decisions"
    glowColor="rose"
    imagePosition="left"
  />

  {/* Feature 3: Automated Extraction */}
  <FeatureSection
    useScrollAnimation={useScrollAnimation}
    title="Zero-Effort Import"
    description="Point Continuum at your Claude Code conversation logs and watch as decisions are automatically extracted, entities are resolved, and your knowledge graph grows — all without lifting a finger."
    imageSrc="/media/import-logs.gif"
    imageAlt="Automated decision extraction from Claude Code conversation logs"
    glowColor="orange"
    imagePosition="right"
  />
</section>
```

**Step 2: Add the FeatureSection component above the default export**

```tsx
const glowColors = {
  violet: "from-violet-500/20 to-violet-500/5",
  rose: "from-rose-500/20 to-rose-500/5",
  orange: "from-orange-500/20 to-orange-500/5",
} as const

function FeatureSection({
  useScrollAnimation: useAnim,
  title,
  description,
  imageSrc,
  imageAlt,
  glowColor,
  imagePosition,
}: {
  useScrollAnimation: typeof useScrollAnimation
  title: string
  description: string
  imageSrc: string
  imageAlt: string
  glowColor: keyof typeof glowColors
  imagePosition: "left" | "right"
}) {
  const { ref, isVisible } = useAnim()

  const textBlock = (
    <div className="flex flex-col justify-center">
      <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-6">
        <span className="gradient-text">{title}</span>
      </h2>
      <p className="text-lg text-slate-400 leading-relaxed">{description}</p>
    </div>
  )

  const imageBlock = (
    <div className="relative">
      <div
        className={`absolute -inset-4 bg-gradient-to-br ${glowColors[glowColor]} rounded-3xl blur-2xl`}
        aria-hidden="true"
      />
      <div className="relative rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.4)]">
        <img src={imageSrc} alt={imageAlt} className="w-full h-auto" loading="lazy" />
      </div>
    </div>
  )

  return (
    <div
      ref={ref}
      className={`max-w-7xl mx-auto px-6 py-16 md:py-24 grid md:grid-cols-2 gap-12 md:gap-16 items-center transition-all duration-700 ${
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
      }`}
    >
      {imagePosition === "left" ? (
        <>
          {imageBlock}
          {textBlock}
        </>
      ) : (
        <>
          {textBlock}
          {imageBlock}
        </>
      )}
    </div>
  )
}
```

**Step 3: Verify**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: add feature highlights with scroll animations"
```

---

### Task 6: Build the "How It Works" Section

**Files:**
- Modify: `apps/web/app/page.tsx`

**Step 1: Add imports for the step icons**

Add to the existing lucide-react import at the top:

```tsx
import { GitBranch, Sparkles, MessageSquare, Scan, Network } from "lucide-react"
```

**Step 2: Replace the `{/* How It Works */}` comment**

Insert after the features `</section>` and before `{/* Tech & Credibility */}`:

```tsx
{/* How It Works */}
<HowItWorks useScrollAnimation={useScrollAnimation} />
```

**Step 3: Add the HowItWorks component above the default export**

```tsx
const steps = [
  {
    number: "01",
    icon: MessageSquare,
    title: "Code with AI",
    description: "Have conversations with Claude Code, Copilot, or any AI assistant while building software.",
  },
  {
    number: "02",
    icon: Scan,
    title: "Extract",
    description: "Continuum parses your conversation logs and uses AI to identify decisions, entities, and rationale.",
  },
  {
    number: "03",
    icon: GitBranch,
    title: "Resolve",
    description: "A 7-stage entity resolution pipeline deduplicates and canonicalizes every technology, pattern, and concept.",
  },
  {
    number: "04",
    icon: Network,
    title: "Visualize",
    description: "Explore your decisions as an interactive knowledge graph — search, filter, and discover connections.",
  },
]

function HowItWorks({ useScrollAnimation: useAnim }: { useScrollAnimation: typeof useScrollAnimation }) {
  const { ref, isVisible } = useAnim()

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <div
          className={`text-center mb-16 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-4">
            How It <span className="gradient-text">Works</span>
          </h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            From conversation to knowledge graph in four steps.
          </p>
        </div>

        {/* Steps grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, i) => (
            <div
              key={step.number}
              className={`relative p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-sm transition-all duration-700 hover:border-violet-500/30 hover:-translate-y-1 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: isVisible ? `${i * 150}ms` : "0ms" }}
            >
              {/* Step number */}
              <span className="text-5xl font-bold text-white/[0.04] absolute top-4 right-4 select-none">
                {step.number}
              </span>

              {/* Icon */}
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 border border-violet-500/20 flex items-center justify-center mb-4">
                <step.icon className="w-5 h-5 text-violet-400" />
              </div>

              {/* Content */}
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>

              {/* Connecting line (not on last item) */}
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-1/2 -right-3 w-6 h-px bg-gradient-to-r from-violet-500/40 to-transparent" aria-hidden="true" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Verify**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: add how-it-works pipeline section"
```

---

### Task 7: Build the Tech Stack & Credibility Section

**Files:**
- Modify: `apps/web/app/page.tsx`

**Step 1: Replace the `{/* Tech & Credibility */}` comment**

Insert after `<HowItWorks />` and before the `<footer>`:

```tsx
{/* Tech & Credibility */}
<TechCredibility
  useScrollAnimation={useScrollAnimation}
  useCountUp={useCountUp}
/>
```

**Step 2: Add the TechCredibility component above the default export**

```tsx
const stats = [
  { value: 838, suffix: "+", label: "Automated Tests" },
  { value: 7, suffix: "-Stage", label: "Entity Resolution" },
  { value: 2048, suffix: "", label: "Embedding Dimensions" },
  { value: 3, suffix: "", label: "Specialized Databases" },
]

const techStack = [
  "Next.js", "React", "FastAPI", "PostgreSQL",
  "Neo4j", "Redis", "NVIDIA", "Docker", "Kubernetes",
]

function TechCredibility({
  useScrollAnimation: useAnim,
  useCountUp: useCount,
}: {
  useScrollAnimation: typeof useScrollAnimation
  useCountUp: typeof useCountUp
}) {
  const { ref, isVisible } = useAnim()

  return (
    <section ref={ref} className="relative py-32">
      <div className="max-w-5xl mx-auto px-6">
        {/* Section header */}
        <div
          className={`text-center mb-16 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Built for <span className="gradient-text">Production</span>
          </h2>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto">
            Enterprise-grade infrastructure behind a research-first product.
          </p>
        </div>

        {/* Stats grid */}
        <div
          className={`grid grid-cols-2 md:grid-cols-4 gap-4 mb-16 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          style={{ transitionDelay: isVisible ? "200ms" : "0ms" }}
        >
          {stats.map((stat) => (
            <StatCard key={stat.label} stat={stat} isVisible={isVisible} useCountUp={useCount} />
          ))}
        </div>

        {/* Tech strip */}
        <div
          className={`flex flex-wrap justify-center gap-4 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          style={{ transitionDelay: isVisible ? "400ms" : "0ms" }}
        >
          {techStack.map((tech) => (
            <div
              key={tech}
              className="px-4 py-2 rounded-xl bg-white/[0.02] border border-white/[0.06] text-sm text-slate-400 hover:text-white hover:border-violet-500/30 transition-all"
            >
              {tech}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function StatCard({
  stat,
  isVisible,
  useCountUp: useCount,
}: {
  stat: (typeof stats)[number]
  isVisible: boolean
  useCountUp: typeof useCountUp
}) {
  const count = useCount(stat.value, isVisible)

  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] text-center hover:border-violet-500/30 transition-all">
      <div className="stat-number text-3xl md:text-4xl mb-1">
        {count.toLocaleString()}
        {stat.suffix}
      </div>
      <div className="text-sm text-slate-400">{stat.label}</div>
    </div>
  )
}
```

**Step 3: Verify**

Run: `cd /Users/shehral/continuum && pnpm build 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add apps/web/app/page.tsx
git commit -m "feat: add tech credibility section with animated counters"
```

---

### Task 8: Final Polish and Typecheck

**Files:**
- Modify: `apps/web/app/page.tsx` (if needed)

**Step 1: Run typecheck**

```bash
cd /Users/shehral/continuum/apps/web && pnpm typecheck 2>&1 | tail -20
```

Fix any type errors found.

**Step 2: Run lint**

```bash
cd /Users/shehral/continuum/apps/web && pnpm lint 2>&1 | tail -20
```

Fix any lint issues found.

**Step 3: Run build**

```bash
cd /Users/shehral/continuum && pnpm build 2>&1 | tail -30
```

Ensure the build succeeds with no errors.

**Step 4: Final commit (if there were fixes)**

```bash
git add -A
git commit -m "fix: resolve typecheck and lint issues for landing page"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Update middleware for public access | `middleware.ts` |
| 2 | Move dashboard to `/dashboard` | `app/page.tsx` → `app/dashboard/page.tsx`, sidebar, login |
| 3 | Landing page shell (nav + footer) | `app/page.tsx` (new) |
| 4 | Hero section with product showcase | `app/page.tsx`, `public/media/` |
| 5 | Feature highlights with scroll animations | `app/page.tsx` |
| 6 | How It Works pipeline section | `app/page.tsx` |
| 7 | Tech credibility with animated counters | `app/page.tsx` |
| 8 | Final typecheck, lint, build | `app/page.tsx` |
