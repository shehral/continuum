"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search as SearchIcon } from "lucide-react"

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
        <div className="px-6 py-4 border-b bg-background">
          <h1 className="text-2xl font-bold tracking-tight">Search</h1>
          <p className="text-sm text-muted-foreground">
            Find decisions, entities, and knowledge across your graph
          </p>
        </div>

        {/* Search Bar */}
        <div className="px-6 py-4 border-b bg-background">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search decisions, concepts, technologies..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button type="submit" disabled={query.length < 2}>
              Search
            </Button>
          </form>

          <Tabs value={searchType} onValueChange={(v) => setSearchType(v as typeof searchType)} className="mt-4">
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="decision">Decisions</TabsTrigger>
              <TabsTrigger value="entity">Entities</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Results */}
        <ScrollArea className="flex-1">
          <div className="p-6 space-y-4">
            {!query && (
              <div className="text-center py-12">
                <SearchIcon className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <p className="text-muted-foreground">
                  Enter a search term to find decisions and entities
                </p>
              </div>
            )}

            {query && isLoading && (
              <div className="text-center py-8">
                <p className="text-muted-foreground">Searching...</p>
              </div>
            )}

            {query && !isLoading && results?.length === 0 && (
              <div className="text-center py-8">
                <p className="text-muted-foreground">No results found for &quot;{query}&quot;</p>
              </div>
            )}

            {results?.map((result) => (
              <Card key={result.id} className="hover:shadow-md transition-shadow cursor-pointer">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={isDecision(result) ? "default" : "secondary"}>
                      {isDecision(result) ? "decision" : "entity"}
                    </Badge>
                    <CardTitle className="text-base">
                      {isDecision(result) ? result.trigger : result.name}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  {isDecision(result) ? (
                    <p className="text-sm text-muted-foreground">
                      {result.decision}
                    </p>
                  ) : (
                    <Badge variant="outline">{result.type}</Badge>
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
