const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface Decision {
  id: string
  trigger: string
  context: string
  options: string[]
  decision: string
  rationale: string
  confidence: number
  created_at: string
  entities: Entity[]
  source?: "claude_logs" | "interview" | "manual" | "unknown"
  project_name?: string
}

export interface Entity {
  id: string
  name: string
  type: "concept" | "system" | "person" | "technology" | "pattern"
}

export interface GraphNode {
  id: string
  type: "decision" | "entity"
  label: string
  data: Decision | Entity
  has_embedding?: boolean
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationship: string
  weight?: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Relationship types
export type RelationshipType =
  | "INVOLVES"
  | "SIMILAR_TO"
  | "SUPERSEDES"
  | "INFLUENCED_BY"
  | "CONTRADICTS"
  | "IS_A"
  | "PART_OF"
  | "RELATED_TO"
  | "DEPENDS_ON"

export interface SimilarDecision {
  id: string
  trigger: string
  decision: string
  similarity: number
  shared_entities: string[]
}

export interface GraphStats {
  decisions: { total: number; with_embeddings: number }
  entities: { total: number; with_embeddings: number }
  relationships: number
}

export interface CaptureSession {
  id: string
  status: "active" | "completed" | "abandoned"
  created_at: string
  updated_at: string
  messages: CaptureMessage[]
}

export interface CaptureMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  extracted_entities?: Entity[]
}

export interface DashboardStats {
  total_decisions: number
  total_entities: number
  total_sessions: number
  recent_decisions: Decision[]
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl
  }

  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    return this.fetch<DashboardStats>("/api/dashboard/stats")
  }

  // Decisions
  async getDecisions(limit = 50, offset = 0): Promise<Decision[]> {
    return this.fetch<Decision[]>(
      `/api/decisions?limit=${limit}&offset=${offset}`
    )
  }

  async getDecision(id: string): Promise<Decision> {
    return this.fetch<Decision>(`/api/decisions/${id}`)
  }

  async deleteDecision(id: string): Promise<{ status: string; message: string }> {
    return this.fetch<{ status: string; message: string }>(
      `/api/decisions/${id}`,
      { method: "DELETE" }
    )
  }

  // Graph
  async getGraph(options?: {
    include_similarity?: boolean
    include_temporal?: boolean
    include_entity_relations?: boolean
    source_filter?: "claude_logs" | "interview" | "manual" | "unknown"
    project_filter?: string
  }): Promise<GraphData> {
    const params = new URLSearchParams()
    if (options?.include_similarity !== undefined)
      params.append("include_similarity", String(options.include_similarity))
    if (options?.include_temporal !== undefined)
      params.append("include_temporal", String(options.include_temporal))
    if (options?.include_entity_relations !== undefined)
      params.append("include_entity_relations", String(options.include_entity_relations))
    if (options?.source_filter)
      params.append("source_filter", options.source_filter)
    if (options?.project_filter)
      params.append("project_filter", options.project_filter)
    const query = params.toString()
    return this.fetch<GraphData>(`/api/graph${query ? `?${query}` : ""}`)
  }

  async getDecisionSources(): Promise<Record<string, number>> {
    return this.fetch<Record<string, number>>("/api/graph/sources")
  }

  async getProjectCounts(): Promise<Record<string, number>> {
    return this.fetch<Record<string, number>>("/api/graph/projects")
  }

  async getNodeDetails(nodeId: string): Promise<GraphNode> {
    return this.fetch<GraphNode>(`/api/graph/nodes/${nodeId}`)
  }

  async getSimilarDecisions(
    nodeId: string,
    topK = 5,
    threshold = 0.5
  ): Promise<SimilarDecision[]> {
    return this.fetch<SimilarDecision[]>(
      `/api/graph/nodes/${nodeId}/similar?top_k=${topK}&threshold=${threshold}`
    )
  }

  async semanticSearch(
    query: string,
    topK = 10,
    threshold = 0.5
  ): Promise<SimilarDecision[]> {
    return this.fetch<SimilarDecision[]>("/api/graph/search/semantic", {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK, threshold }),
    })
  }

  async getGraphStats(): Promise<GraphStats> {
    return this.fetch<GraphStats>("/api/graph/stats")
  }

  async getRelationshipTypes(): Promise<Record<string, number>> {
    return this.fetch<Record<string, number>>("/api/graph/relationships/types")
  }


  // Entities
  async deleteEntity(id: string): Promise<{ status: string; message: string }> {
    return this.fetch<{ status: string; message: string }>(
      `/api/entities/${id}`,
      { method: "DELETE" }
    )
  }


  // Capture Sessions
  async startCaptureSession(projectName?: string | null): Promise<CaptureSession> {
    return this.fetch<CaptureSession>("/api/capture/sessions", {
      method: "POST",
      ...(projectName && {
        body: JSON.stringify({ project_name: projectName }),
      }),
    })
  }

  async getCaptureSession(id: string): Promise<CaptureSession> {
    return this.fetch<CaptureSession>(`/api/capture/sessions/${id}`)
  }

  async sendCaptureMessage(
    sessionId: string,
    content: string
  ): Promise<CaptureMessage> {
    return this.fetch<CaptureMessage>(
      `/api/capture/sessions/${sessionId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      }
    )
  }

  async completeCaptureSession(id: string): Promise<CaptureSession> {
    return this.fetch<CaptureSession>(`/api/capture/sessions/${id}/complete`, {
      method: "POST",
    })
  }

  // Ingestion
  async getAvailableProjects(): Promise<{
    dir: string
    name: string
    files: number
    path: string
  }[]> {
    return this.fetch("/api/ingest/projects")
  }

  async previewIngestion(options?: {
    project?: string
    exclude?: string[]
    limit?: number
  }): Promise<{
    total_conversations: number
    previews: { file: string; project: string; messages: number; preview: string }[]
    project_filter: string | null
    exclude_projects: string[]
  }> {
    const params = new URLSearchParams()
    if (options?.project) params.append("project", options.project)
    if (options?.exclude?.length) params.append("exclude", options.exclude.join(","))
    if (options?.limit) params.append("limit", String(options.limit))
    return this.fetch(`/api/ingest/preview?${params}`)
  }

  async triggerIngestion(options?: {
    project?: string
    exclude?: string[]
  }): Promise<{ status: string; processed: number; decisions_extracted: number }> {
    const params = new URLSearchParams()
    if (options?.project) params.append("project", options.project)
    if (options?.exclude?.length) params.append("exclude", options.exclude.join(","))
    return this.fetch<{ status: string; processed: number; decisions_extracted: number }>(
      `/api/ingest/trigger?${params}`,
      { method: "POST" }
    )
  }

  async getIngestionStatus(): Promise<{
    is_watching: boolean
    last_run: string | null
    files_processed: number
  }> {
    return this.fetch<{
      is_watching: boolean
      last_run: string | null
      files_processed: number
    }>("/api/ingest/status")
  }

  async resetGraph(): Promise<{ status: string; message: string }> {
    return this.fetch("/api/graph/reset?confirm=true", { method: "DELETE" })
  }

  // Search
  async search(
    query: string,
    type?: "decision" | "entity"
  ): Promise<(Decision | Entity)[]> {
    const params = new URLSearchParams({ query })
    if (type) params.append("type", type)
    return this.fetch<(Decision | Entity)[]>(`/api/search?${params}`)
  }

  // Create decision manually
  async createDecision(data: {
    trigger: string
    context: string
    options: string[]
    decision: string
    rationale: string
    entities: string[]
    project_name?: string | null
  }): Promise<Decision> {
    return this.fetch<Decision>("/api/decisions", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  // Entity linking
  async linkEntity(
    decisionId: string,
    entityId: string,
    relationship: string
  ): Promise<void> {
    await this.fetch(`/api/entities/link`, {
      method: "POST",
      body: JSON.stringify({
        decision_id: decisionId,
        entity_id: entityId,
        relationship,
      }),
    })
  }

  async getSuggestedEntities(text: string): Promise<Entity[]> {
    return this.fetch<Entity[]>("/api/entities/suggest", {
      method: "POST",
      body: JSON.stringify({ text }),
    })
  }

  // Hybrid search combining lexical and semantic search
  async hybridSearch(
    query: string,
    options?: {
      topK?: number
      threshold?: number
      alpha?: number
      searchDecisions?: boolean
      searchEntities?: boolean
    }
  ): Promise<HybridSearchResult[]> {
    const body = {
      query,
      top_k: options?.topK ?? 10,
      threshold: options?.threshold ?? 0.3,
      alpha: options?.alpha ?? 0.3,
      search_decisions: options?.searchDecisions ?? true,
      search_entities: options?.searchEntities ?? true,
    }
    return this.fetch<HybridSearchResult[]>("/api/graph/search/hybrid", {
      method: "POST",
      body: JSON.stringify(body),
    })
  }
}

export const api = new ApiClient()

// Hybrid search types and methods
export interface HybridSearchResult {
  id: string
  type: "decision" | "entity"
  label: string
  lexical_score: number
  semantic_score: number
  combined_score: number
  data: {
    trigger?: string
    decision?: string
    context?: string
    rationale?: string
    created_at?: string
    source?: string
    name?: string
    type?: string
    aliases?: string[]
  }
  matched_fields: string[]
}

export type SearchMode = "hybrid" | "lexical" | "semantic"
