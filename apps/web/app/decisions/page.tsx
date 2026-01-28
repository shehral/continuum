"use client"

import { useState, useEffect } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Search, Filter, ChevronDown, Plus } from "lucide-react"

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
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{decision.trigger}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Context
              </h4>
              <p className="text-sm">{decision.context}</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Options Considered
              </h4>
              <ul className="list-disc list-inside text-sm space-y-1">
                {decision.options.map((option, i) => (
                  <li key={i}>{option}</li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Decision
              </h4>
              <p className="text-sm font-medium">{decision.decision}</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-1">
                Rationale
              </h4>
              <p className="text-sm">{decision.rationale}</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">
                Related Entities
              </h4>
              <div className="flex flex-wrap gap-2">
                {decision.entities.map((entity) => (
                  <Badge key={entity.id} variant="secondary">
                    {entity.name}
                    <span className="ml-1 text-xs opacity-60">
                      ({entity.type})
                    </span>
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t">
              <span>
                Confidence: {Math.round(decision.confidence * 100)}%
              </span>
              <span>
                Created: {new Date(decision.created_at).toLocaleDateString()}
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Decision Manually</DialogTitle>
          <DialogDescription>
            Record a decision trace when AI extraction is unavailable
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="trigger">Trigger / Problem</Label>
            <Input
              id="trigger"
              placeholder="What prompted this decision?"
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="context">Context</Label>
            <textarea
              id="context"
              className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Background information, constraints, requirements..."
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="options">Options Considered (one per line)</Label>
            <textarea
              id="options"
              className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Option A&#10;Option B&#10;Option C"
              value={options}
              onChange={(e) => setOptions(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="decision">Decision</Label>
            <Input
              id="decision"
              placeholder="What was decided?"
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rationale">Rationale</Label>
            <textarea
              id="rationale"
              className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Why was this decision made?"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="entities">Related Entities (comma-separated)</Label>
            <Input
              id="entities"
              placeholder="PostgreSQL, React, API Design..."
              value={entities}
              onChange={(e) => setEntities(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!trigger || !decision || createMutation.isPending}
          >
            {createMutation.isPending ? "Saving..." : "Save Decision"}
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
        <div className="px-6 py-4 border-b bg-background">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Decisions</h1>
              <p className="text-sm text-muted-foreground">
                Browse and search captured decision traces
              </p>
            </div>
            <Button onClick={() => setShowAddDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Decision
            </Button>
          </div>

          {/* Search and filters */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search decisions, entities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" />
              Filter
              <ChevronDown className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </div>

        {/* Decision list */}
        <ScrollArea className="flex-1">
          <div className="p-6 space-y-4">
            {isLoading ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">Loading decisions...</p>
              </div>
            ) : !filteredDecisions?.length ? (
              <Card className="p-8 text-center">
                <p className="text-muted-foreground mb-4">
                  {searchQuery
                    ? "No decisions match your search"
                    : "No decisions captured yet"}
                </p>
                {!searchQuery && (
                  <Button onClick={() => setShowAddDialog(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Your First Decision
                  </Button>
                )}
              </Card>
            ) : (
              filteredDecisions.map((decision) => (
                <Card
                  key={decision.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setSelectedDecision(decision)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base">
                        {decision.trigger}
                      </CardTitle>
                      <Badge variant="secondary">
                        {Math.round(decision.confidence * 100)}%
                      </Badge>
                    </div>
                    <CardDescription className="line-clamp-2">
                      {decision.decision}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex flex-wrap gap-1">
                        {decision.entities.slice(0, 4).map((entity) => (
                          <Badge key={entity.id} variant="outline" className="text-xs">
                            {entity.name}
                          </Badge>
                        ))}
                        {decision.entities.length > 4 && (
                          <Badge variant="outline" className="text-xs">
                            +{decision.entities.length - 4}
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(decision.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))
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
