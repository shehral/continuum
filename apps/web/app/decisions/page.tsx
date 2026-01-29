"use client"

import { useState, useEffect } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Search, Filter, ChevronDown, Plus, Loader2, FileText } from "lucide-react"

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
import { api, type Decision } from "@/lib/api"
import { getEntityStyle } from "@/lib/constants"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

// Confidence badge styling based on level
const getConfidenceStyle = (confidence: number) => {
  if (confidence >= 0.8) return "bg-green-500/20 text-green-400 border-green-500/30"
  if (confidence >= 0.6) return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
  return "bg-orange-500/20 text-orange-400 border-orange-500/30"
}

function DecisionDetailDialog({
  decision,
  open,
  onOpenChange,
}: {
  decision: Decision | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!decision) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col bg-slate-900/95 border-white/10 backdrop-blur-xl">
        <DialogHeader>
          <DialogTitle className="text-slate-100 text-xl">{decision.trigger}</DialogTitle>
          <Badge className={`w-fit ${getConfidenceStyle(decision.confidence)}`}>
            {Math.round(decision.confidence * 100)}% confidence
          </Badge>
        </DialogHeader>
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-5">
            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-medium text-cyan-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                Context
              </h4>
              <p className="text-sm text-slate-300 leading-relaxed">{decision.context}</p>
            </div>

            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-medium text-purple-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                Options Considered
              </h4>
              <ul className="space-y-2">
                {decision.options.map((option, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-slate-500 font-mono">{i + 1}.</span>
                    {option}
                  </li>
                ))}
              </ul>
            </div>

            <div className="p-4 rounded-lg bg-gradient-to-r from-cyan-500/10 to-teal-500/10 border border-cyan-500/20">
              <h4 className="text-sm font-medium text-cyan-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                Decision
              </h4>
              <p className="text-sm font-medium text-slate-200">{decision.decision}</p>
            </div>

            <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <h4 className="text-sm font-medium text-green-400 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                Rationale
              </h4>
              <p className="text-sm text-slate-300 leading-relaxed">{decision.rationale}</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-slate-400 mb-3">
                Related Entities
              </h4>
              <div className="flex flex-wrap gap-2">
                {decision.entities.map((entity) => {
                  const style = getEntityStyle(entity.type)
                  return (
                    <Badge
                      key={entity.id}
                      className={`${style.bg} ${style.text} ${style.border} hover:scale-105 transition-transform`}
                    >
                      {style.icon} {entity.name}
                    </Badge>
                  )
                })}
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-500 pt-4 border-t border-white/[0.06]">
              <span>
                Created {new Date(decision.created_at).toLocaleDateString()}
              </span>
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

  const createMutation = useMutation({
    mutationFn: () =>
      api.createDecision({
        trigger,
        context,
        options: options.split("\n").filter((o) => o.trim()),
        decision,
        rationale,
        entities: entities.split(",").map((e) => e.trim()).filter(Boolean),
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
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
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

export default function DecisionsPage() {
  const queryClient = useQueryClient()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)

  // Open add dialog if ?add=true is in URL
  useEffect(() => {
    if (searchParams.get("add") === "true") {
      setShowAddDialog(true)
      // Clear the query param
      router.replace("/decisions", { scroll: false })
    }
  }, [searchParams, router])

  const { data: decisions, isLoading } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => api.getDecisions(),
  })

  const filteredDecisions = decisions?.filter(
    (d) =>
      d.trigger.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.decision.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.entities.some((e) =>
        e.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
  )

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
            <Button
              onClick={() => setShowAddDialog(true)}
              className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)] hover:shadow-[0_6px_20px_rgba(34,211,238,0.4)] hover:scale-105 transition-all"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Decision
            </Button>
          </div>

          {/* Search and filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <Input
                placeholder="Search decisions, entities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-white/[0.05] border-white/[0.1] text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/50 focus:ring-cyan-500/20"
              />
            </div>
            <Button
              variant="outline"
              className="border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100"
            >
              <Filter className="h-4 w-4 mr-2" />
              Filter
              <ChevronDown className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </div>

        {/* Decision list */}
        <ScrollArea className="flex-1 bg-slate-900/30">
          <div className="p-6 space-y-4">
            {isLoading ? (
              <div className="text-center py-12 animate-in fade-in duration-300">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-cyan-400" />
                <p className="text-slate-400">Loading decisions...</p>
              </div>
            ) : !filteredDecisions?.length ? (
              <div className="text-center py-16 animate-in fade-in duration-500">
                <div className="mx-auto mb-4 h-20 w-20 rounded-2xl bg-cyan-500/10 flex items-center justify-center">
                  <FileText className="h-10 w-10 text-cyan-400/50" />
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
                    <Plus className="h-4 w-4 mr-2" />
                    Add Your First Decision
                  </Button>
                )}
              </div>
            ) : (
              filteredDecisions.map((decision, index) => {
                return (
                  <Card
                    key={decision.id}
                    className="bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.06] hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] hover:scale-[1.01] transition-all duration-300 cursor-pointer group animate-in fade-in slide-in-from-bottom-4"
                    style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'backwards' }}
                    onClick={() => setSelectedDecision(decision)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-3">
                        <CardTitle className="text-base text-slate-200 group-hover:text-cyan-300 transition-colors leading-tight">
                          {decision.trigger}
                        </CardTitle>
                        <Badge className={`shrink-0 ${getConfidenceStyle(decision.confidence)}`}>
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
                          <TooltipContent side="bottom" className="max-w-sm">
                            <p>{decision.decision}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between">
                        <div className="flex flex-wrap gap-1.5">
                          {decision.entities.slice(0, 4).map((entity) => {
                            const style = getEntityStyle(entity.type)
                            return (
                              <Badge
                                key={entity.id}
                                className={`text-xs ${style.bg} ${style.text} ${style.border}`}
                              >
                                {style.icon} {entity.name}
                              </Badge>
                            )
                          })}
                          {decision.entities.length > 4 && (
                            <Badge className="text-xs bg-slate-500/20 text-slate-400 border-slate-500/30">
                              +{decision.entities.length - 4} more
                            </Badge>
                          )}
                        </div>
                        <span className="text-xs text-slate-500">
                          {new Date(decision.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                )
              })
            )}
          </div>
        </ScrollArea>

        <DecisionDetailDialog
          decision={selectedDecision}
          open={!!selectedDecision}
          onOpenChange={(open) => !open && setSelectedDecision(null)}
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
      </div>
    </AppShell>
  )
}
