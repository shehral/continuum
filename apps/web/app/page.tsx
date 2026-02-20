"use client"

import React, { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { GitBranch, Sparkles, MessageSquare, Scan, Network } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeroGraph } from "@/components/landing/hero-graph"
import { PulsingNetwork } from "@/components/landing/pulsing-network"
import { ConversationExtract } from "@/components/landing/conversation-extract"
import { FileScan } from "@/components/landing/file-scan"
import { ChatAnimation, ScanAnimation, MergeAnimation, GraphAnimation } from "@/components/landing/step-animations"
import { AmbientParticles } from "@/components/landing/ambient-particles"

// ─── Hooks ───────────────────────────────────────────────

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

// ─── Feature Section Component ───────────────────────────

const glowColors = {
  violet: "from-violet-500/20 to-violet-500/5",
  rose: "from-rose-500/20 to-rose-500/5",
  orange: "from-orange-500/20 to-orange-500/5",
} as const

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
  animation?: (isVisible: boolean) => React.ReactNode
}) {
  const { ref, isVisible } = useScrollAnimation()

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
      <div className="relative space-y-4">
        {animation && (
          <div className="rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.4)] bg-[hsl(250,20%,4%)] p-4 md:p-6">
            {animation(isVisible)}
          </div>
        )}
        <div className="rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.4)]">
          <img src={imageSrc} alt={imageAlt} className="w-full h-auto" loading="lazy" />
        </div>
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

// ─── How It Works Component ──────────────────────────────

const steps = [
  {
    number: "01",
    icon: MessageSquare,
    title: "Code with AI",
    description:
      "Have conversations with Claude Code, Copilot, or any AI assistant while building software.",
  },
  {
    number: "02",
    icon: Scan,
    title: "Extract",
    description:
      "Continuum parses your conversation logs and uses AI to identify decisions, entities, and rationale.",
  },
  {
    number: "03",
    icon: GitBranch,
    title: "Resolve",
    description:
      "A 7-stage entity resolution pipeline deduplicates and canonicalizes every technology, pattern, and concept.",
  },
  {
    number: "04",
    icon: Network,
    title: "Visualize",
    description:
      "Explore your decisions as an interactive knowledge graph — search, filter, and discover connections.",
  },
]

const stepAnimationComponents = [ChatAnimation, ScanAnimation, MergeAnimation, GraphAnimation]

function HowItWorks() {
  const { ref, isVisible } = useScrollAnimation()

  return (
    <section ref={ref} className="relative py-32 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6">
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

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, i) => (
            <div
              key={step.number}
              className={`relative p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-sm transition-all duration-700 hover:border-violet-500/30 hover:-translate-y-1 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
              }`}
              style={{ transitionDelay: isVisible ? `${i * 150}ms` : "0ms" }}
            >
              <span className="text-5xl font-bold text-white/[0.04] absolute top-4 right-4 select-none">
                {step.number}
              </span>

              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 border border-violet-500/20 flex items-center justify-center mb-4">
                {(() => {
                  const StepAnim = stepAnimationComponents[i]
                  return StepAnim ? <StepAnim isVisible={isVisible} /> : <step.icon className="w-5 h-5 text-violet-400" />
                })()}
              </div>

              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>

              {i < steps.length - 1 && (
                <div
                  className="hidden lg:block absolute top-1/2 -right-3 w-6 h-px bg-gradient-to-r from-violet-500/40 to-transparent"
                  aria-hidden="true"
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Tech Credibility Component ──────────────────────────

const stats = [
  { value: 838, suffix: "+", label: "Automated Tests" },
  { value: 7, suffix: "-Stage", label: "Entity Resolution" },
  { value: 2048, suffix: "", label: "Embedding Dimensions" },
  { value: 3, suffix: "", label: "Specialized Databases" },
]

const techStack = [
  "Next.js",
  "React",
  "FastAPI",
  "PostgreSQL",
  "Neo4j",
  "Redis",
  "NVIDIA",
  "Docker",
  "Kubernetes",
]

function StatCard({ stat, isVisible }: { stat: (typeof stats)[number]; isVisible: boolean }) {
  const count = useCountUp(stat.value, isVisible)

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

function TechCredibility() {
  const { ref, isVisible } = useScrollAnimation()

  return (
    <section ref={ref} className="relative py-32">
      <div className="max-w-5xl mx-auto px-6">
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

        <div
          className={`grid grid-cols-2 md:grid-cols-4 gap-4 mb-16 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
          style={{ transitionDelay: isVisible ? "200ms" : "0ms" }}
        >
          {stats.map((stat) => (
            <StatCard key={stat.label} stat={stat} isVisible={isVisible} />
          ))}
        </div>

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

// ─── Main Landing Page ───────────────────────────────────

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
      {mounted && <AmbientParticles />}

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
      <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-16">
        {mounted && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
            <div className="absolute top-1/4 left-[16%] w-72 h-72 bg-violet-500/12 rounded-full blur-3xl animate-float" />
            <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-fuchsia-500/8 rounded-full blur-3xl animate-float [animation-delay:-1.5s]" />
            <div className="absolute top-1/2 right-[16%] w-56 h-56 bg-orange-500/6 rounded-full blur-3xl animate-float [animation-delay:-3s]" />
          </div>
        )}

        <div className="relative z-10 max-w-4xl mx-auto text-center animate-in fade-in slide-in-from-bottom-8 duration-1000">
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

          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            Continuum captures the engineering decisions hidden in your AI coding
            sessions and transforms them into a searchable knowledge graph.
          </p>

          <div className="relative mx-auto max-w-5xl">
            <div
              className="absolute -inset-4 bg-gradient-to-r from-violet-500/20 via-fuchsia-500/10 to-orange-500/20 rounded-3xl blur-2xl opacity-60"
              aria-hidden="true"
            />
            <div className="relative rounded-2xl border border-white/[0.08] overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.5)] bg-[hsl(250,20%,4%)] p-4 md:p-8">
              <HeroGraph />
            </div>
          </div>
        </div>

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-pulse-glow">
          <span className="text-xs text-slate-500">Scroll to explore</span>
          <div className="w-5 h-8 rounded-full border border-white/20 flex items-start justify-center p-1">
            <div className="w-1 h-2 rounded-full bg-violet-400 animate-slide-in-down" />
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="relative py-32">
        <FeatureSection
          title="See the Connections"
          description="Every decision creates a ripple. Continuum maps how your technology choices, design patterns, and architectural decisions interconnect — revealing relationships you never noticed."
          imageSrc="/media/knowledge-graph.gif"
          imageAlt="Interactive knowledge graph visualization showing decision and entity nodes"
          glowColor="violet"
          imagePosition="right"
          animation={(visible) => <PulsingNetwork isVisible={visible} />}
        />

        <FeatureSection
          title="Capture What Matters"
          description="An AI interviewer guides you through structured decision capture — extracting the trigger, context, options, and rationale behind every choice. No more lost tribal knowledge."
          imageSrc="/media/capture-session.gif"
          imageAlt="AI-guided interview session capturing engineering decisions"
          glowColor="rose"
          imagePosition="left"
          animation={(visible) => <ConversationExtract isVisible={visible} />}
        />

        <FeatureSection
          title="Zero-Effort Import"
          description="Point Continuum at your Claude Code conversation logs and watch as decisions are automatically extracted, entities are resolved, and your knowledge graph grows — all without lifting a finger."
          imageSrc="/media/import-logs.gif"
          imageAlt="Automated decision extraction from Claude Code conversation logs"
          glowColor="orange"
          imagePosition="right"
          animation={(visible) => <FileScan isVisible={visible} />}
        />
      </section>

      {/* How It Works */}
      <HowItWorks />

      {/* Tech & Credibility */}
      <TechCredibility />

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
            <a
              href="mailto:shehral.m@northeastern.edu"
              className="hover:text-violet-400 transition-colors"
            >
              Contact
            </a>
            <Link href="/login" className="hover:text-violet-400 transition-colors">
              Sign In
            </Link>
          </div>
          <p className="text-xs text-slate-600 mt-4">&copy; 2026 Ali Shehral</p>
        </div>
      </footer>
    </div>
  )
}
