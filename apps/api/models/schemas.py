from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# Entity schemas
class EntityBase(BaseModel):
    name: str
    type: str  # concept, system, person, technology, pattern


class Entity(EntityBase):
    id: Optional[str] = None  # Optional for creation, always present in response


# Decision source types
class DecisionSource:
    CLAUDE_LOGS = "claude_logs"  # Extracted from Claude Code conversation logs
    INTERVIEW = "interview"      # Captured via AI-guided interview
    MANUAL = "manual"            # Manually entered by user
    UNKNOWN = "unknown"          # Legacy or untagged decisions


# Decision schemas
class DecisionBase(BaseModel):
    trigger: str
    context: str
    options: list[str]
    decision: str
    rationale: str


class Decision(DecisionBase):
    id: str
    confidence: float
    created_at: datetime
    entities: list[Entity]
    source: str = DecisionSource.UNKNOWN  # Where this decision came from


class DecisionCreate(DecisionBase):
    confidence: float = 0.8
    source: str = DecisionSource.UNKNOWN


# Graph schemas
class GraphNode(BaseModel):
    id: str
    type: str  # decision, entity
    label: str
    data: dict
    has_embedding: bool = False


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    weight: Optional[float] = None  # Confidence/similarity score


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# Enhanced relationship types
class RelationshipType:
    # Decision -> Entity
    INVOLVES = "INVOLVES"

    # Decision -> Decision
    SIMILAR_TO = "SIMILAR_TO"
    SUPERSEDES = "SUPERSEDES"
    INFLUENCED_BY = "INFLUENCED_BY"
    CONTRADICTS = "CONTRADICTS"

    # Entity -> Entity
    IS_A = "IS_A"
    PART_OF = "PART_OF"
    RELATED_TO = "RELATED_TO"
    DEPENDS_ON = "DEPENDS_ON"


# Semantic search schemas
class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    threshold: float = 0.5
    include_entities: bool = True


class SimilarDecision(BaseModel):
    id: str
    trigger: str
    decision: str
    similarity: float
    shared_entities: list[str] = []


class EntityRelationship(BaseModel):
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship: str
    confidence: float = 1.0


# Capture session schemas
class CaptureMessageBase(BaseModel):
    role: str
    content: str


class CaptureMessage(CaptureMessageBase):
    id: str
    timestamp: datetime
    extracted_entities: Optional[list[Entity]] = None


class CaptureSessionBase(BaseModel):
    status: str = "active"


class CaptureSession(CaptureSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    messages: list[CaptureMessage] = []


# Dashboard schemas
class DashboardStats(BaseModel):
    total_decisions: int
    total_entities: int
    total_sessions: int
    recent_decisions: list[Decision]


# Ingestion schemas
class IngestionStatus(BaseModel):
    is_watching: bool
    last_run: Optional[datetime]
    files_processed: int


class IngestionResult(BaseModel):
    status: str
    processed: int
    decisions_extracted: int


# Search schemas
class SearchResult(BaseModel):
    type: str  # decision, entity
    id: str
    label: str
    score: float
    data: dict


# Entity linking schemas
class LinkEntityRequest(BaseModel):
    decision_id: str
    entity_id: str
    relationship: str


class SuggestEntitiesRequest(BaseModel):
    text: str
