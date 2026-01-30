"""Pydantic schemas with input validation (SEC-005 compliant)."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# SEC-005: UUID pattern for ID validation
UUID_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.IGNORECASE)

# SEC-005: Valid relationship types (whitelist)
VALID_RELATIONSHIP_TYPES = frozenset({
    # Decision -> Entity
    "INVOLVES",
    # Decision -> Decision
    "SIMILAR_TO",
    "SUPERSEDES",
    "INFLUENCED_BY",
    "CONTRADICTS",
    # Entity -> Entity
    "IS_A",
    "PART_OF",
    "RELATED_TO",
    "DEPENDS_ON",
    "ALTERNATIVE_TO",
})


def validate_uuid(value: str, field_name: str = "id") -> str:
    """Validate that a string is a valid UUID format (SEC-005)."""
    if not UUID_PATTERN.match(value):
        raise ValueError(f"{field_name} must be a valid UUID format")
    return value.lower()  # Normalize to lowercase


# Entity schemas
class EntityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    type: str = Field(..., min_length=1, max_length=50)  # concept, system, person, technology, pattern


class Entity(EntityBase):
    id: Optional[str] = Field(None, max_length=36)  # Optional for creation, always present in response


# Decision source types
class DecisionSource:
    CLAUDE_LOGS = "claude_logs"  # Extracted from Claude Code conversation logs
    INTERVIEW = "interview"      # Captured via AI-guided interview
    MANUAL = "manual"            # Manually entered by user
    UNKNOWN = "unknown"          # Legacy or untagged decisions


# Decision schemas
class DecisionBase(BaseModel):
    trigger: str = Field(..., min_length=1, max_length=5000)
    context: str = Field(..., min_length=1, max_length=10000)
    options: list[str] = Field(..., min_length=1, max_length=50)
    decision: str = Field(..., min_length=1, max_length=5000)
    rationale: str = Field(..., min_length=1, max_length=10000)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str]) -> list[str]:
        """Validate each option string."""
        if not v:
            raise ValueError("At least one option is required")
        validated = []
        for opt in v:
            if not opt or len(opt) > 1000:
                raise ValueError("Each option must be 1-1000 characters")
            validated.append(opt.strip())
        return validated


class Decision(DecisionBase):
    id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime
    entities: list[Entity]
    source: str = DecisionSource.UNKNOWN  # Where this decision came from


class DecisionCreate(DecisionBase):
    confidence: float = Field(0.8, ge=0.0, le=1.0)
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
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)  # Confidence/similarity score


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
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(10, ge=1, le=100)
    threshold: float = Field(0.5, ge=0.0, le=1.0)
    include_entities: bool = True


class SimilarDecision(BaseModel):
    id: str
    trigger: str
    decision: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    shared_entities: list[str] = []


class EntityRelationship(BaseModel):
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship: str
    confidence: float = Field(1.0, ge=0.0, le=1.0)


# Capture session schemas
class CaptureMessageBase(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=50000)


class CaptureMessage(CaptureMessageBase):
    id: str
    timestamp: datetime
    extracted_entities: Optional[list[Entity]] = None


class CaptureSessionBase(BaseModel):
    status: str = Field("active", pattern=r"^(active|completed|cancelled)$")


class CaptureSession(CaptureSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    messages: list[CaptureMessage] = []


# Dashboard schemas
class DashboardStats(BaseModel):
    total_decisions: int = Field(..., ge=0)
    total_entities: int = Field(..., ge=0)
    total_sessions: int = Field(..., ge=0)
    recent_decisions: list[Decision]


# Ingestion schemas
class IngestionStatus(BaseModel):
    is_watching: bool
    last_run: Optional[datetime]
    files_processed: int = Field(..., ge=0)


class IngestionResult(BaseModel):
    status: str
    processed: int = Field(..., ge=0)
    decisions_extracted: int = Field(..., ge=0)


# Search schemas
class SearchResult(BaseModel):
    type: str  # decision, entity
    id: str
    label: str
    score: float = Field(..., ge=0.0, le=1.0)
    data: dict


# Entity linking schemas (SEC-005: Hardened with validation)
class LinkEntityRequest(BaseModel):
    """Request to link an entity to a decision.

    SEC-005: All fields are validated to prevent injection and ensure data integrity.
    """
    decision_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the decision to link to"
    )
    entity_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the entity to link"
    )
    relationship: str = Field(
        default="INVOLVES",
        max_length=50,
        description="Type of relationship"
    )

    @field_validator("decision_id")
    @classmethod
    def validate_decision_id(cls, v: str) -> str:
        """Validate decision_id is a proper UUID (SEC-005)."""
        return validate_uuid(v, "decision_id")

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, v: str) -> str:
        """Validate entity_id is a proper UUID (SEC-005)."""
        return validate_uuid(v, "entity_id")

    @field_validator("relationship")
    @classmethod
    def validate_relationship(cls, v: str) -> str:
        """Validate relationship is in the allowed list (SEC-005)."""
        v_upper = v.upper()
        if v_upper not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Invalid relationship type: '{v}'. "
                f"Allowed types: {', '.join(sorted(VALID_RELATIONSHIP_TYPES))}"
            )
        return v_upper


class SuggestEntitiesRequest(BaseModel):
    """Request to get entity suggestions from text."""
    text: str = Field(..., min_length=1, max_length=10000)


# Hybrid search schemas (KG-P1-3)
class HybridSearchRequest(BaseModel):
    """Request for hybrid search combining lexical and semantic search.

    Hybrid search combines:
    - Lexical search (fulltext index) - good for exact matches and keywords
    - Semantic search (vector similarity) - good for meaning and concepts

    Final score = alpha * lexical_score + (1 - alpha) * semantic_score
    """
    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum combined score threshold")
    alpha: float = Field(0.3, ge=0.0, le=1.0, description="Weight for lexical score (0.3 = 30% lexical, 70% semantic)")
    include_entities: bool = Field(True, description="Include entities in search results")
    search_decisions: bool = Field(True, description="Search decision nodes")
    search_entities: bool = Field(True, description="Search entity nodes")


class HybridSearchResult(BaseModel):
    """Result from hybrid search with score breakdown."""
    id: str
    type: str  # "decision" or "entity"
    label: str
    lexical_score: float = Field(..., ge=0.0, le=1.0)
    semantic_score: float = Field(..., ge=0.0, le=1.0)
    combined_score: float = Field(..., ge=0.0, le=1.0)
    data: dict
    matched_fields: list[str] = Field(default_factory=list, description="Fields that matched lexically")
