"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search as SearchIcon, Loader2 } from "lucide-react"

import { AppShell } from "@/components/layout/app-shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, type Decision, type Entity } from "@/lib/api"

// Type guard to check if result is a Decision
function isDecision(result: Decision | Entity): result is Decision {
  return "trigger" in result && "decision" in result
}

// Entity type styling
const entityStyles: Record<string, { icon: string; bg: string; text: string; border: string }> = {
  technology: { icon: "🔧", bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30" },
  concept: { icon: "💡", bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30" },
  system: { icon: "⚙️", bg: "bg-green-500/10", text: "text-green-400", border: "border-green-500/30" },
  pattern: { icon: "🧩", bg: "bg-orange-500/10", text: "text-orange-400", border: "border-orange-500/30" },
  person: { icon: "👤", bg: "bg-pink-500/10", text: "text-pink-400", border: "border-pink-500/30" },
  organization: { icon: "🏢", bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/30" },
}

const getEntityStyle = (type: string) => entityStyles[type] || entityStyles.concept

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [searchType, setSearchType] = useState<"all" | "decision" | "entity">("all")

  const { data: results, isLoading, refetch } = useQuery({
    queryKey: ["search", query, searchType],
    queryFn: () => api.search(query, searchType === "all" ? undefined : searchType),
    enabled: query.length >= 2,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.length >= 2) {
      refetch()
    }
  }

  return (
    <AppShell>
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.06] bg-slate-900/80 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-500">
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Search</h1>
          <p className="text-sm text-slate-400">
            Find decisions, entities, and knowledge across your graph
          </p>
        </div>

        {/* Search Bar */}
        <div className="px-6 py-4 border-b border-white/[0.06] bg-slate-900/50">
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <Input
                placeholder="Search decisions, concepts, technologies..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-10 bg-white/[0.05] border-white/[0.1] text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/50 focus:ring-cyan-500/20"
              />
            </div>
            <Button
              type="submit"
              disabled={query.length < 2}
              className="bg-gradient-to-r from-cyan-500 to-teal-400 text-slate-900 hover:shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all disabled:opacity-50"
            >
              <SearchIcon className="h-4 w-4 mr-2" />
              Search
            </Button>
          </form>

          <Tabs value={searchType} onValueChange={(v) => setSearchType(v as typeof searchType)} className="mt-4">
            <TabsList className="bg-white/[0.05] border border-white/[0.1]">
              <TabsTrigger value="all" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">All</TabsTrigger>
              <TabsTrigger value="decision" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Decisions</TabsTrigger>
              <TabsTrigger value="entity" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Entities</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Results */}
        <ScrollArea className="flex-1 bg-slate-900/30">
          <div className="p-6 space-y-4">
            {!query && (
              <div className="text-center py-16 animate-in fade-in duration-500">
                <div className="mx-auto mb-4 h-20 w-20 rounded-2xl bg-cyan-500/10 flex items-center justify-center">
                  <SearchIcon className="h-10 w-10 text-cyan-400/50" />
                </div>
                <p className="text-slate-400 text-lg">
                  Enter a search term to find decisions and entities
                </p>
                <p className="text-slate-500 text-sm mt-2">
                  Try searching for technologies, concepts, or decision triggers
                </p>
              </div>
            )}

            {query && isLoading && (
              <div className="text-center py-12 animate-in fade-in duration-300">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-cyan-400" />
                <p className="text-slate-400">Searching for &quot;{query}&quot;...</p>
              </div>
            )}

            {query && !isLoading && results?.length === 0 && (
              <div className="text-center py-12 animate-in fade-in duration-300">
                <div className="mx-auto mb-4 h-16 w-16 rounded-2xl bg-slate-500/10 flex items-center justify-center">
                  <span className="text-3xl">🔍</span>
                </div>
                <p className="text-slate-400">No results found for &quot;{query}&quot;</p>
                <p className="text-slate-500 text-sm mt-2">Try a different search term</p>
              </div>
            )}

            {results?.map((result, index) => (
              <Card
                key={result.id}
                className="bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.06] hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] transition-all duration-300 cursor-pointer group animate-in fade-in slide-in-from-bottom-4"
                style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'backwards' }}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    {isDecision(result) ? (
                      <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30">
                        📋 Decision
                      </Badge>
                    ) : (
                      <Badge className={`${getEntityStyle(result.type).bg} ${getEntityStyle(result.type).text} ${getEntityStyle(result.type).border}`}>
                        {getEntityStyle(result.type).icon} {result.type}
                      </Badge>
                    )}
                    <CardTitle className="text-base text-slate-200 group-hover:text-cyan-300 transition-colors">
                      {isDecision(result) ? result.trigger : result.name}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  {isDecision(result) ? (
                    <p className="text-sm text-slate-400 line-clamp-2">
                      {result.decision}
                    </p>
                  ) : (
                    <p className="text-sm text-slate-500">
                      Click to view in knowledge graph
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>
    </AppShell>
  )
}
