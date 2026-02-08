"use client"

import { useState, useEffect, useCallback, useRef, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useVirtualizer } from "@tanstack/react-virtual"
import { Search, Filter, ChevronDown, Plus, Loader2, FileText, Trash2, X, Calendar, Info, Upload, Lightbulb } from "lucide-react"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { DeleteConfirmDialog } from "@/components/ui/confirm-dialog"
import { ErrorState } from "@/components/ui/error-state"
import { DecisionListSkeleton } from "@/components/ui/skeleton"
import { api, type Decision } from "@/lib/api"
import { getEntityStyle } from "@/lib/constants"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ProjectSelector } from "@/components/projects/project-selector"
import { Slider } from "@/components/ui/slider"

// Confidence badge styling based on level (Product-QW-1: Enhanced with tooltips)
const getConfidenceStyle = (confidence: number) => {
  if (confidence >= 0.8) return "bg-green-500/20 text-green-400 border-green-500/30"
  if (confidence >= 0.6) return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
  return "bg-orange-500/20 text-orange-400 border-orange-500/30"
}

// Get confidence explanation for tooltips (Product-QW-1)
const getConfidenceExplanation = (confidence: number): { level: string; description: string } => {
  if (confidence >= 0.8) {
    return {
      level: "High Confidence",
      description: "Strong decision with clear rationale and well-defined context. The extraction has high accuracy.",
    }
  }
  if (confidence >= 0.6) {
    return {
      level: "Medium Confidence",
      description: "Good decision trace but may have some ambiguity in context or rationale. Consider reviewing for completeness.",
    }
  }
  return {
    level: "Low Confidence",
    description: "Decision may need review. Could have unclear trigger, missing context, or incomplete rationale.",
  }
}

// Date range filter options (Product-QW-2)
const DATE_RANGE_OPTIONS = [
  { label: "Today", value: "today", days: 0 },
  { label: "Last 7 days", value: "week", days: 7 },
  { label: "Last 30 days", value: "month", days: 30 },
  { label: "All time", value: "all", days: -1 },
] as const

type DateRangeValue = typeof DATE_RANGE_OPTIONS[number]["value"]

// Helper to check if a date is within the selected range (Product-QW-2)
function isWithinDateRange(dateStr: string, range: DateRangeValue): boolean {
  if (range === "all") return true
  const date = new Date(dateStr)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())

  if (range === "today") {
    return date >= startOfToday
  }

  const option = DATE_RANGE_OPTIONS.find(o => o.value === range)
  if (!option || option.days < 0) return true

  const cutoff = new Date(startOfToday)
  cutoff.setDate(cutoff.getDate() - option.days)
  return date >= cutoff
}

// Reusable ConfidenceBadge component with tooltip (Product-QW-1)
function ConfidenceBadge({
  confidence,
  className = "",
  showPercentOnly = false
}: {
  confidence: number
  className?: string
  showPercentOnly?: boolean
}) {
  const explanation = getConfidenceExplanation(confidence)
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            className={`cursor-help ${getConfidenceStyle(confidence)} ${className}`}
            aria-label={`${Math.round(confidence * 100)}% confidence - ${explanation.level}`}
          >
            {showPercentOnly
              ? `${Math.round(confidence * 100)}%`
              : `${Math.round(confidence * 100)}% confidence`}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Info className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              <span className="font-medium text-slate-200">{explanation.level}</span>
            </div>
            <p className="text-xs text-slate-400">{explanation.description}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

// Date range filter component (Product-QW-2)
function DateRangeFilter({
  value,
  onChange,
}: {
  value: DateRangeValue
  onChange: (value: DateRangeValue) => void
}) {
  return (
    <div className="flex gap-1" role="group" aria-label="Date range filter">
      {DATE_RANGE_OPTIONS.map((option) => (
        <Button
          key={option.value}
          variant={value === option.value ? "default" : "ghost"}
          size="sm"
          onClick={() => onChange(option.value)}
          className={
            value === option.value
              ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/30 h-7 text-xs"
              : "text-slate-400 hover:text-slate-200 h-7 text-xs"
          }
        >
          {option.label}
        </Button>
      ))}
    </div>
  )
}

function DecisionDetailDialog({
  decision,
  open,
  onOpenChange,
  onDelete,
}: {
  decision: Decision | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDelete: (decision: Decision) => void
}) {
  if (!decision) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col bg-slate-900/95 border-white/10 backdrop-blur-xl">
        <DialogHeader>
          <div className="flex items-start justify-between gap-4 pr-8">
            <DialogTitle className="text-slate-100 text-xl">{decision.trigger}</DialogTitle>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDelete(decision)}
                    className="h-8 w-8 text-slate-400 hover:text-red-400 hover:bg-red-500/10 shrink-0"
                    aria-label="Delete decision"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Delete this decision</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <Badge className={`w-fit ` + getConfidenceStyle(decision.confidence)}>
            {Math.round(decision.confidence * 100)}% confidence
          </Badge>
        </DialogHeader>
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-5">
            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-medium text-cyan-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" aria-hidden="true" />
                Context
              </h4>
              <p className="text-sm text-slate-300 leading-relaxed">{decision.context}</p>
            </div>

            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-medium text-purple-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" aria-hidden="true" />
                Options Considered
              </h4>
              <ul className="space-y-2" role="list" aria-label="Options considered">
                {decision.options.map((option, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-slate-500 font-mono" aria-hidden="true">{i + 1}.</span>
                    {option}
                  </li>
                ))}
              </ul>
            </div>

            <div className="p-4 rounded-lg bg-gradient-to-r from-cyan-500/10 to-teal-500/10 border border-cyan-500/20">
              <h4 className="text-sm font-medium text-cyan-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" aria-hidden="true" />
                Decision
              </h4>
              <p className="text-sm font-medium text-slate-200">{decision.decision}</p>
            </div>

            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-medium text-green-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" aria-hidden="true" />
                Rationale
              </h4>
              <p className="text-sm text-slate-300 leading-relaxed">{decision.rationale}</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-3">
                Related Entities
              </h4>
              <div className="flex flex-wrap gap-2" role="list" aria-label="Related entities">
                {decision.entities.map((entity) => {
                  const style = getEntityStyle(entity.type)
                  return (
                    <Badge
                      key={entity.id}
                      className={`${style.bg} ${style.text} ${style.border} hover:scale-105 transition-transform`}
                      role="listitem"
                    >
                      <style.lucideIcon className="h-3 w-3 mr-1" aria-hidden="true" />
                      {entity.name}
                    </Badge>
                  )
                })}
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-500 pt-4 border-t border-white/[0.06]">
              <span>
                Created {new Date(decision.created_at).toLocaleDateString()}
              </span>
              {decision.source && decision.source !== "unknown" && (
                <Badge className={`text-[10px] px-1.5 py-0 ${
                  decision.source === "claude_logs" ? "bg-violet-500/15 text-violet-300 border-violet-400/30" :
                  decision.source === "interview" ? "bg-cyan-500/15 text-cyan-300 border-cyan-400/30" :
                  "bg-slate-500/15 text-slate-300 border-slate-400/30"
                }`}>
                  {decision.source === "claude_logs" ? "claude-log" : decision.source}
                </Badge>
              )}
              {decision.project_name && (
                <Badge className="text-[10px] px-1.5 py-0 bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-400/30">
                  {decision.project_name}
                </Badge>
              )}
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}

function AddDecisionDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [trigger, setTrigger] = useState("")
  const [context, setContext] = useState("")
  const [options, setOptions] = useState("")
  const [decision, setDecision] = useState("")
  const [rationale, setRationale] = useState("")
  const [entities, setEntities] = useState("")
  const [selectedProject, setSelectedProject] = useState<string | null>(null)

  const { data: projectCounts } = useQuery({
    queryKey: ["project-counts"],
    queryFn: () => api.getProjectCounts(),
    staleTime: 5 * 60 * 1000,
  })

  const projects = Object.keys(projectCounts || {}).filter((p) => p !== "unassigned")

  const createMutation = useMutation({
    mutationFn: () =>
      api.createDecision({
        trigger,
        context,
        options: options.split("\n").filter((o) => o.trim()),
        decision,
        rationale,
        entities: entities.split(",").map((e) => e.trim()).filter(Boolean),
        project_name: selectedProject,
      }),
    onSuccess: () => {
      onSuccess()
      onOpenChange(false)
      // Reset form
      setTrigger("")
      setContext("")
      setOptions("")
      setDecision("")
      setRationale("")
      setEntities("")
      setSelectedProject(null)
    },
  })

  const inputClass = "bg-white/[0.05] border-white/[0.1] text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/50 focus:ring-cyan-500/20"
  const textareaClass = "w-full min-h-[80px] rounded-md border bg-white/[0.05] border-white/[0.1] text-slate-200 placeholder:text-slate-500 px-3 py-2 text-sm focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 focus:outline-none"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-slate-900/95 border-white/10 backdrop-blur-xl">
        <DialogHeader>
          <DialogTitle className="text-slate-100 text-xl">Add Decision Manually</DialogTitle>
          <DialogDescription className="text-slate-400">
            Record a decision trace when AI extraction is unavailable
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="trigger" className="text-slate-300">Trigger / Problem</Label>
            <Input
              id="trigger"
              placeholder="What prompted this decision?"
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
              className={inputClass}
              aria-required="true"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="context" className="text-slate-300">Context</Label>
            <textarea
              id="context"
              className={textareaClass}
              placeholder="Background information, constraints, requirements..."
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="options" className="text-slate-300">Options Considered (one per line)</Label>
            <textarea
              id="options"
              className={textareaClass}
              placeholder="Option A&#10;Option B&#10;Option C"
              value={options}
              onChange={(e) => setOptions(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="decision" className="text-slate-300">Decision</Label>
            <Input
              id="decision"
              placeholder="What was decided?"
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              className={inputClass}
              aria-required="true"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rationale" className="text-slate-300">Rationale</Label>
            <textarea
              id="rationale"
              className={textareaClass}
              placeholder="Why was this decision made?"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="entities" className="text-slate-300">Related Entities (comma-separated)</Label>
            <Input
              id="entities"
              placeholder="PostgreSQL, React, API Design..."
              value={entities}
              onChange={(e) => setEntities(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="project" className="text-slate-300">
              Project <span className="text-slate-500 font-normal">(optional)</span>
            </Label>
            <ProjectSelector
              value={selectedProject}
              onChange={setSelectedProject}
              projects={projects}
              placeholder="Select or create project..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100"
          >
            Cancel
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!trigger || !decision || createMutation.isPending}
            className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 hover:shadow-[0_0_20px_rgba(34,211,238,0.3)] disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden="true" />
                Saving...
              </>
            ) : (
              "Save Decision"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


// Confidence-based left border accent for decision cards
const getConfidenceBorderAccent = (confidence: number) => {
  if (confidence >= 0.8) return "border-l-2 border-l-emerald-500/60"
  if (confidence >= 0.6) return "border-l-2 border-l-amber-500/60"
  return "border-l-2 border-l-rose-500/60"
}

// Decision card component for virtual list (P1-3: Virtual scrolling)
function DecisionCard({
  decision,
  onClick,
  onKeyDown,
  style,
}: {
  decision: Decision
  onClick: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
  style?: React.CSSProperties
}) {
  return (
    <div style={style} className="pb-4">
      <Card
        role="listitem"
        tabIndex={0}
        className={`bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.06] hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] hover:scale-[1.01] transition-all duration-300 cursor-pointer group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 ${getConfidenceBorderAccent(decision.confidence)}`}
        onClick={onClick}
        onKeyDown={onKeyDown}
        aria-label={`Decision: ${decision.trigger}`}
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-3">
            <CardTitle className="text-base text-slate-200 group-hover:text-cyan-300 transition-colors leading-tight">
              {decision.trigger}
            </CardTitle>
            <Badge className={`shrink-0 ` + getConfidenceStyle(decision.confidence)}>
              {Math.round(decision.confidence * 100)}%
            </Badge>
          </div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <CardDescription className="text-slate-400 line-clamp-2 mt-1 cursor-help">
                  {decision.decision}
                </CardDescription>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-lg">
                <p>{decision.decision}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1.5 mb-2" role="list" aria-label="Related entities">
            {decision.entities.slice(0, 4).map((entity) => {
              const style = getEntityStyle(entity.type)
              return (
                <Badge
                  key={entity.id}
                  className={`text-xs ${style.bg} ${style.text} ${style.border}`}
                  role="listitem"
                >
                  <style.lucideIcon className="h-3 w-3 mr-1" aria-hidden="true" />
                  {entity.name}
                </Badge>
              )
            })}
            {decision.entities.length > 4 && (
              <Badge className="text-xs bg-slate-500/20 text-slate-400 border-slate-500/30">
                +{decision.entities.length - 4} more
              </Badge>
            )}
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {decision.source && decision.source !== "unknown" && (
                <Badge className={`text-[10px] px-1.5 py-0 ${
                  decision.source === "claude_logs" ? "bg-violet-500/15 text-violet-300 border-violet-400/30" :
                  decision.source === "interview" ? "bg-cyan-500/15 text-cyan-300 border-cyan-400/30" :
                  "bg-slate-500/15 text-slate-300 border-slate-400/30"
                }`}>
                  {decision.source === "claude_logs" ? "claude-log" : decision.source}
                </Badge>
              )}
              {decision.project_name && (
                <Badge className="text-[10px] px-1.5 py-0 bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-400/30">
                  {decision.project_name}
                </Badge>
              )}
            </div>
            <span className="text-xs text-slate-500">
              {new Date(decision.created_at).toLocaleDateString()}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Virtual list component for decisions (P1-3: Virtual scrolling for performance)
function VirtualDecisionList({
  decisions,
  onCardClick,
  onCardKeyDown,
}: {
  decisions: Decision[]
  onCardClick: (decision: Decision) => void
  onCardKeyDown: (e: React.KeyboardEvent, decision: Decision) => void
}) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: decisions.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 140, // Estimated card height including margin
    overscan: 5, // Render 5 extra items above/below viewport
  })

  return (
    <div
      ref={parentRef}
      className="flex-1 overflow-auto p-6"
      style={{ contain: "strict" }}
    >
      <div
        role="list"
        aria-label="Decision list"
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const decision = decisions[virtualItem.index]
          return (
            <DecisionCard
              key={decision.id}
              decision={decision}
              onClick={() => onCardClick(decision)}
              onKeyDown={(e) => onCardKeyDown(e, decision)}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualItem.start}px)`,
              }}
            />
          )
        })}
      </div>
    </div>
  )
}

function DecisionsPageContent() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Decision | null>(null)

  // Filter state (P0-2) - synced with URL params
  const [sourceFilter, setSourceFilter] = useState<string>(searchParams.get("source") || "all")
  const [confidenceFilter, setConfidenceFilter] = useState<number>(
    parseInt(searchParams.get("minConfidence") || "0", 10)
  )
  const [filterOpen, setFilterOpen] = useState(false)
  // Date range filter state (Product-QW-2)
  const [dateRangeFilter, setDateRangeFilter] = useState<DateRangeValue>(
    (searchParams.get("dateRange") as DateRangeValue) || "all"
  )

  // Count active filters for badge
  const activeFilterCount =
    (sourceFilter !== "all" ? 1 : 0) +
    (confidenceFilter > 0 ? 1 : 0) +
    (dateRangeFilter !== "all" ? 1 : 0)

  // Update URL when filters change
  const updateFiltersInUrl = useCallback((source: string, confidence: number, dateRange: DateRangeValue = "all") => {
    const params = new URLSearchParams(searchParams.toString())
    if (source !== "all") {
      params.set("source", source)
    } else {
      params.delete("source")
    }
    if (confidence > 0) {
      params.set("minConfidence", confidence.toString())
    } else {
      params.delete("minConfidence")
    }
    if (dateRange !== "all") {
      params.set("dateRange", dateRange)
    } else {
      params.delete("dateRange")
    }
    const newUrl = params.toString() ? `?${params.toString()}` : "/decisions"
    router.replace(newUrl, { scroll: false })
  }, [searchParams, router])

  const handleSourceChange = useCallback((value: string) => {
    setSourceFilter(value)
    updateFiltersInUrl(value, confidenceFilter, dateRangeFilter)
  }, [confidenceFilter, dateRangeFilter, updateFiltersInUrl])

  const handleConfidenceChange = useCallback((value: number[]) => {
    const newValue = value[0]
    setConfidenceFilter(newValue)
    updateFiltersInUrl(sourceFilter, newValue, dateRangeFilter)
  }, [sourceFilter, dateRangeFilter, updateFiltersInUrl])

  const handleDateRangeChange = useCallback((value: DateRangeValue) => {
    setDateRangeFilter(value)
    updateFiltersInUrl(sourceFilter, confidenceFilter, value)
  }, [sourceFilter, confidenceFilter, updateFiltersInUrl])

  const clearFilters = useCallback(() => {
    setSourceFilter("all")
    setConfidenceFilter(0)
    setDateRangeFilter("all")
    router.replace("/decisions", { scroll: false })
  }, [router])

  // Open add dialog if ?add=true is in URL
  useEffect(() => {
    if (searchParams.get("add") === "true") {
      setShowAddDialog(true)
      // Clear the query param
      router.replace("/decisions", { scroll: false })
    }
  }, [searchParams, router])

  const { data: decisions, isLoading, error, refetch } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => api.getDecisions(),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDecision(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decisions"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      queryClient.invalidateQueries({ queryKey: ["graph"] })
      setDeleteTarget(null)
      setSelectedDecision(null)
    },
  })

  const handleDeleteClick = useCallback((decision: Decision) => {
    setDeleteTarget(decision)
  }, [])

  const handleDeleteConfirm = useCallback(async () => {
    if (deleteTarget) {
      await deleteMutation.mutateAsync(deleteTarget.id)
    }
  }, [deleteTarget, deleteMutation])

  const handleCardClick = useCallback((decision: Decision) => {
    setSelectedDecision(decision)
  }, [])

  const handleCardKeyDown = useCallback((e: React.KeyboardEvent, decision: Decision) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      setSelectedDecision(decision)
    }
  }, [])

  const filteredDecisions = decisions?.filter((d) => {
    // Text search filter
    const matchesSearch = searchQuery === "" ||
      d.trigger.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.decision.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.entities.some((e) =>
        e.name.toLowerCase().includes(searchQuery.toLowerCase())
      )

    // Source filter (P0-2)
    const matchesSource = sourceFilter === "all" ||
      (d.source || "unknown") === sourceFilter

    // Confidence filter (P0-2) - minConfidence as percentage
    const matchesConfidence = d.confidence >= (confidenceFilter / 100)

    // Date range filter (Product-QW-2)
    const matchesDateRange = isWithinDateRange(d.created_at, dateRangeFilter)

    return matchesSearch && matchesSource && matchesConfidence && matchesDateRange
  })

  // Determine if filters are active (for empty state)
  const hasActiveFilters = sourceFilter !== "all" || confidenceFilter > 0 || dateRangeFilter !== "all"

  // Determine if we should use virtual scrolling (P1-3)
  // Use virtual scrolling when we have more than 20 items for performance
  const useVirtualScrolling = (filteredDecisions?.length ?? 0) > 20

  return (
    <AppShell>
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.06] bg-slate-900/80 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">Decisions</h1>
              <p className="text-sm text-slate-400">
                Browse and search captured decision traces
                {decisions?.length ? (
                  <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                    {decisions.length} total
                  </span>
                ) : null}
              </p>
            </div>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={() => setShowAddDialog(true)}
                    className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)] hover:shadow-[0_6px_20px_rgba(34,211,238,0.4)] hover:scale-105 transition-all"
                    aria-label="Add new decision"
                  >
                    <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
                    Add Decision
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Manually add a decision trace</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {/* Search and filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" aria-hidden="true" />
              <Input
                placeholder="Search decisions, entities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-white/[0.05] border-white/[0.1] text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/50 focus:ring-cyan-500/20"
                aria-label="Search decisions"
              />
            </div>
            {/* Date range quick filters (Product-QW-2) */}
            <div className="hidden md:flex items-center gap-2 px-2 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <Calendar className="h-4 w-4 text-slate-500" aria-hidden="true" />
              <DateRangeFilter value={dateRangeFilter} onChange={handleDateRangeChange} />
            </div>
            <Popover open={filterOpen} onOpenChange={setFilterOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100 relative"
                  aria-label="Filter decisions"
                >
                  <Filter className="h-4 w-4 mr-2" aria-hidden="true" />
                  Filter
                  {activeFilterCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-cyan-500 text-[10px] font-bold text-slate-900 flex items-center justify-center">
                      {activeFilterCount}
                    </span>
                  )}
                  <ChevronDown className="h-4 w-4 ml-2" aria-hidden="true" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-72 bg-slate-900/95 border-white/10 backdrop-blur-xl" align="end">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-slate-200">Filters</h4>
                    {activeFilterCount > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearFilters}
                        className="h-7 text-xs text-slate-400 hover:text-slate-200"
                      >
                        <X className="h-3 w-3 mr-1" />
                        Clear all
                      </Button>
                    )}
                  </div>

                  {/* Source filter */}
                  <div className="space-y-2">
                    <Label className="text-sm text-slate-400">Source</Label>
                    <div className="flex flex-wrap gap-1.5">
                      {["all", "claude_logs", "interview", "manual", "unknown"].map((source) => (
                        <Button
                          key={source}
                          variant={sourceFilter === source ? "default" : "outline"}
                          size="sm"
                          onClick={() => handleSourceChange(source)}
                          className={
                            sourceFilter === source
                              ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/30"
                              : "border-white/10 text-slate-400 hover:text-slate-200"
                          }
                        >
                          {source === "all" ? "All" : source.replace("_", " ")}
                        </Button>
                      ))}
                    </div>
                  </div>

                  {/* Confidence filter */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm text-slate-400">Min Confidence</Label>
                      <span className="text-sm font-medium text-cyan-400">
                        {confidenceFilter}%
                      </span>
                    </div>
                    <Slider
                      value={[confidenceFilter]}
                      onValueChange={handleConfidenceChange}
                      min={0}
                      max={100}
                      step={10}
                      className="py-2"
                    />
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>0%</span>
                      <span>50%</span>
                      <span>100%</span>
                    </div>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>

        {/* Decision list */}
        {isLoading ? (
          <div className="p-6" aria-live="polite" aria-busy="true">
            <DecisionListSkeleton count={5} />
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState
              title="Failed to load decisions"
              message="We couldn't load your decisions. Please try again."
              error={error instanceof Error ? error : null}
              retry={() => refetch()}
            />
          </div>
        ) : !filteredDecisions?.length ? (
          <div className="text-center py-16 animate-in fade-in duration-500 p-6">
            <div className="mx-auto mb-4 h-20 w-20 rounded-2xl bg-cyan-500/10 flex items-center justify-center">
              <FileText className="h-10 w-10 text-cyan-400/50" aria-hidden="true" />
            </div>
            <p className="text-slate-300 text-lg mb-2">
              {searchQuery
                ? `No decisions match "${searchQuery}"`
                : "No decisions captured yet"}
            </p>
            <p className="text-slate-500 text-sm mb-6">
              {searchQuery
                ? "Try a different search term"
                : "Start by adding a decision manually or extract from Claude logs"}
            </p>
            {!searchQuery && (
              <Button
                onClick={() => setShowAddDialog(true)}
                className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 hover:shadow-[0_0_20px_rgba(34,211,238,0.3)]"
              >
                <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
                Add Your First Decision
              </Button>
            )}
          </div>
        ) : useVirtualScrolling ? (
          // Virtual scrolling for large lists (P1-3)
          <VirtualDecisionList
            decisions={filteredDecisions}
            onCardClick={handleCardClick}
            onCardKeyDown={handleCardKeyDown}
          />
        ) : (
          // Regular scrolling for small lists (preserves animations)
          <ScrollArea className="flex-1 bg-slate-900/30">
            <div className="p-6 space-y-4">
              <div role="list" aria-label="Decision list">
                {filteredDecisions.map((decision, index) => (
                  <Card
                    key={decision.id}
                    role="listitem"
                    tabIndex={0}
                    className={`bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.06] hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] hover:scale-[1.01] transition-all duration-300 cursor-pointer group animate-in fade-in slide-in-from-bottom-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 mb-4 ${getConfidenceBorderAccent(decision.confidence)}`}
                    style={{ animationDelay: `${index * 50}ms`, animationFillMode: "backwards" }}
                    onClick={() => handleCardClick(decision)}
                    onKeyDown={(e) => handleCardKeyDown(e, decision)}
                    aria-label={`Decision: ${decision.trigger}`}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-3">
                        <CardTitle className="text-base text-slate-200 group-hover:text-cyan-300 transition-colors leading-tight">
                          {decision.trigger}
                        </CardTitle>
                        <Badge className={`shrink-0 ` + getConfidenceStyle(decision.confidence)}>
                          {Math.round(decision.confidence * 100)}%
                        </Badge>
                      </div>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <CardDescription className="text-slate-400 line-clamp-2 mt-1 cursor-help">
                              {decision.decision}
                            </CardDescription>
                          </TooltipTrigger>
                          <TooltipContent side="bottom" className="max-w-lg">
                            <p>{decision.decision}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-1.5 mb-2" role="list" aria-label="Related entities">
                        {decision.entities.slice(0, 4).map((entity) => {
                          const style = getEntityStyle(entity.type)
                          return (
                            <Badge
                              key={entity.id}
                              className={`text-xs ${style.bg} ${style.text} ${style.border}`}
                              role="listitem"
                            >
                              <style.lucideIcon className="h-3 w-3 mr-1" aria-hidden="true" />
                              {entity.name}
                            </Badge>
                          )
                        })}
                        {decision.entities.length > 4 && (
                          <Badge className="text-xs bg-slate-500/20 text-slate-400 border-slate-500/30">
                            +{decision.entities.length - 4} more
                            </Badge>
                          )}
                        </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {decision.source && decision.source !== "unknown" && (
                            <Badge className={`text-[10px] px-1.5 py-0 ${
                              decision.source === "claude_logs" ? "bg-violet-500/15 text-violet-300 border-violet-400/30" :
                              decision.source === "interview" ? "bg-cyan-500/15 text-cyan-300 border-cyan-400/30" :
                              "bg-slate-500/15 text-slate-300 border-slate-400/30"
                            }`}>
                              {decision.source === "claude_logs" ? "claude-log" : decision.source}
                            </Badge>
                          )}
                          {decision.project_name && (
                            <Badge className="text-[10px] px-1.5 py-0 bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-400/30">
                              {decision.project_name}
                            </Badge>
                          )}
                        </div>
                        <span className="text-xs text-slate-500">
                          {new Date(decision.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </ScrollArea>
        )}

        <DecisionDetailDialog
          decision={selectedDecision}
          open={!!selectedDecision}
          onOpenChange={(open) => !open && setSelectedDecision(null)}
          onDelete={handleDeleteClick}
        />

        <AddDecisionDialog
          open={showAddDialog}
          onOpenChange={setShowAddDialog}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ["decisions"] })
            queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
            queryClient.invalidateQueries({ queryKey: ["graph"] })
          }}
        />

        <DeleteConfirmDialog
          open={!!deleteTarget}
          onOpenChange={(open) => !open && setDeleteTarget(null)}
          itemType="Decision"
          itemName={deleteTarget?.trigger}
          onConfirm={handleDeleteConfirm}
          isLoading={deleteMutation.isPending}
        />
      </div>
    </AppShell>
  )
}

export default function DecisionsPage() {
  return (
    <Suspense fallback={
      <AppShell>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppShell>
    }>
      <DecisionsPageContent />
    </Suspense>
  )
}
