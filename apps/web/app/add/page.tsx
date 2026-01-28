"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  FolderOpen,
  MessageSquarePlus,
  PenLine,
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileJson,
} from "lucide-react"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"

type IngestionStatus = "idle" | "running" | "success" | "error"

export default function AddKnowledgePage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [ingestionStatus, setIngestionStatus] = useState<IngestionStatus>("idle")
  const [ingestionResult, setIngestionResult] = useState<{ processed: number } | null>(null)

  const ingestionMutation = useMutation({
    mutationFn: () => api.triggerIngestion(),
    onMutate: () => {
      setIngestionStatus("running")
    },
    onSuccess: (data) => {
      setIngestionStatus("success")
      setIngestionResult({ processed: data.processed })
      queryClient.invalidateQueries({ queryKey: ["decisions"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })
      queryClient.invalidateQueries({ queryKey: ["graph"] })
    },
    onError: () => {
      setIngestionStatus("error")
    },
  })

  const methods = [
    {
      id: "import",
      title: "Import from Claude Code",
      description: "Automatically parse your Claude Code conversation logs and extract decision traces using AI.",
      icon: FolderOpen,
      badge: "Automatic",
      badgeVariant: "default" as const,
      details: [
        "Scans ~/.claude/projects for conversation logs",
        "Uses Gemini AI to extract decisions",
        "Identifies entities and relationships",
        "Zero manual effort required",
      ],
      action: (
        <div className="space-y-3">
          <Button
            onClick={() => ingestionMutation.mutate()}
            disabled={ingestionStatus === "running"}
            className="w-full bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)] hover:shadow-[0_6px_20px_rgba(34,211,238,0.4)]"
          >
            {ingestionStatus === "running" ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Scanning logs...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Scan &amp; Import
              </>
            )}
          </Button>
          {ingestionStatus === "success" && ingestionResult && (
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              Processed {ingestionResult.processed} files
            </div>
          )}
          {ingestionStatus === "error" && (
            <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
              <AlertCircle className="h-4 w-4" />
              Import failed. Check if Gemini API quota is available.
            </div>
          )}
        </div>
      ),
    },
    {
      id: "capture",
      title: "Capture with AI Interview",
      description: "Have a guided conversation with an AI interviewer that helps you document decisions step by step.",
      icon: MessageSquarePlus,
      badge: "Interactive",
      badgeVariant: "secondary" as const,
      details: [
        "AI guides you through the decision trace",
        "Extracts entities as you talk",
        "Suggests links to existing knowledge",
        "Best for complex, nuanced decisions",
      ],
      action: (
        <Button
          onClick={() => router.push("/capture")}
          className="w-full bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 font-semibold shadow-[0_4px_16px_rgba(34,211,238,0.3)] hover:shadow-[0_6px_20px_rgba(34,211,238,0.4)]"
        >
          <MessageSquarePlus className="h-4 w-4 mr-2" />
          Start Interview
        </Button>
      ),
    },
    {
      id: "manual",
      title: "Quick Manual Entry",
      description: "Directly fill out a form to add a decision when you already know all the details.",
      icon: PenLine,
      badge: "Quick",
      badgeVariant: "outline" as const,
      details: [
        "Simple form-based entry",
        "No AI processing required",
        "Works offline or when AI quota exhausted",
        "Best for straightforward decisions",
      ],
      action: (
        <Button
          onClick={() => router.push("/decisions?add=true")}
          variant="outline"
          className="w-full bg-white/[0.05] border-white/10 text-slate-300 hover:bg-white/[0.08] hover:text-slate-100"
        >
          <PenLine className="h-4 w-4 mr-2" />
          Add Manually
        </Button>
      ),
    },
  ]

  return (
    <AppShell>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-100">Add Knowledge</h1>
          <p className="text-slate-400">
            Choose how you want to add decisions to your knowledge graph
          </p>
        </div>

        {/* Method Cards */}
        <div className="grid gap-6 md:grid-cols-3">
          {methods.map((method) => (
            <Card key={method.id} className="flex flex-col bg-white/[0.03] backdrop-blur-xl border-white/[0.06]">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                    <method.icon className="h-5 w-5 text-cyan-400" />
                  </div>
                  <Badge
                    variant={method.badgeVariant}
                    className={method.badgeVariant === "default"
                      ? "bg-cyan-500/20 text-cyan-400 border-cyan-500/30"
                      : method.badgeVariant === "secondary"
                      ? "bg-slate-500/20 text-slate-300 border-slate-500/30"
                      : "bg-white/[0.05] text-slate-400 border-white/10"
                    }
                  >
                    {method.badge}
                  </Badge>
                </div>
                <CardTitle className="mt-4 text-slate-100">{method.title}</CardTitle>
                <CardDescription className="text-slate-400">{method.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                <ul className="text-sm text-slate-400 space-y-2 mb-6 flex-1">
                  {method.details.map((detail, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-cyan-400 mt-1">•</span>
                      {detail}
                    </li>
                  ))}
                </ul>
                {method.action}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Info Section */}
        <Card className="bg-white/[0.03] backdrop-blur-xl border-white/[0.06]">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="h-10 w-10 rounded-xl bg-blue-500/10 flex items-center justify-center shrink-0">
                <FileJson className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <h3 className="font-medium mb-1 text-slate-100">How Import Works</h3>
                <p className="text-sm text-slate-400">
                  The import feature scans your Claude Code conversation logs stored at{" "}
                  <code className="px-1.5 py-0.5 bg-white/[0.05] rounded text-cyan-400 border border-white/10">~/.claude/projects</code>.
                  It uses AI to analyze conversations and extract structured decision traces
                  including the trigger, context, options considered, final decision, and rationale.
                  Each decision is linked to relevant entities (technologies, concepts, patterns)
                  to build your knowledge graph.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
