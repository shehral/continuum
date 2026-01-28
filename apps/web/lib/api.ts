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

  // Graph
  async getGraph(options?: {
    include_similarity?: boolean
    include_temporal?: boolean
    include_entity_relations?: boolean
    source_filter?: "claude_logs" | "interview" | "manual" | "unknown"
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
    const query = params.toString()
    return this.fetch<GraphData>(`/api/graph${query ? `?${query}` : ""}`)
  }

  async getDecisionSources(): Promise<Record<string, number>> {
    return this.fetch<Record<string, number>>("/api/graph/sources")
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

  // Capture Sessions
  async startCaptureSession(): Promise<CaptureSession> {
    return this.fetch<CaptureSession>("/api/capture/sessions", {
      method: "POST",
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
  async triggerIngestion(): Promise<{ status: string; processed: number }> {
    return this.fetch<{ status: string; processed: number }>(
      "/api/ingest/trigger",
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
}

export const api = new ApiClient()
