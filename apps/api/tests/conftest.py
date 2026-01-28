"""Shared pytest fixtures for Continuum API tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from models.ontology import ResolvedEntity


# ============================================================================
# Neo4j Session Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_session():
    """Create a mock Neo4j async session."""
    session = AsyncMock()

    # Default empty result
    empty_result = AsyncMock()
    empty_result.single = AsyncMock(return_value=None)
    empty_result.__aiter__ = lambda self: self
    empty_result.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

    session.run = AsyncMock(return_value=empty_result)
    return session


@pytest.fixture
def mock_neo4j_result():
    """Factory for creating mock Neo4j query results."""
    def _create_result(records=None, single_value=None):
        result = AsyncMock()

        if single_value is not None:
            result.single = AsyncMock(return_value=single_value)
        else:
            result.single = AsyncMock(return_value=None)

        if records:
            # Create an async iterator
            async def async_iter():
                for record in records:
                    yield record
            result.__aiter__ = lambda: async_iter()
        else:
            async def empty_iter():
                return
                yield  # Make it a generator
            result.__aiter__ = lambda: empty_iter()

        return result

    return _create_result


# ============================================================================
# LLM Client Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value="Mock LLM response")
    return client


@pytest.fixture
def mock_llm_json_response():
    """Factory for creating mock LLM JSON responses."""
    def _create_response(data):
        import json
        return json.dumps(data)
    return _create_response


# ============================================================================
# Embedding Service Fixtures
# ============================================================================


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock()

    # Default: return a simple 2048-dimension embedding
    def make_embedding(text="", **kwargs):
        # Create deterministic embedding based on text hash
        seed = hash(text) % 1000000
        return [float((seed + i) % 100) / 100.0 for i in range(2048)]

    service.embed_text = AsyncMock(side_effect=make_embedding)
    service.embed_texts = AsyncMock(return_value=[[0.1] * 2048])
    service.embed_decision = AsyncMock(return_value=[0.1] * 2048)
    service.embed_entity = AsyncMock(return_value=[0.1] * 2048)
    service.dimensions = 2048

    return service


@pytest.fixture
def sample_embedding():
    """Return a sample 2048-dimension embedding vector."""
    return [0.1 * (i % 10) for i in range(2048)]


# ============================================================================
# Entity Fixtures
# ============================================================================


@pytest.fixture
def sample_entities():
    """Return sample entity data."""
    return [
        {"id": str(uuid4()), "name": "PostgreSQL", "type": "technology"},
        {"id": str(uuid4()), "name": "Redis", "type": "technology"},
        {"id": str(uuid4()), "name": "Microservices", "type": "concept"},
        {"id": str(uuid4()), "name": "REST API", "type": "pattern"},
    ]


@pytest.fixture
def sample_resolved_entity():
    """Return a sample ResolvedEntity."""
    return ResolvedEntity(
        id=str(uuid4()),
        name="PostgreSQL",
        type="technology",
        is_new=False,
        match_method="exact",
        confidence=1.0,
    )


# ============================================================================
# Decision Fixtures
# ============================================================================


@pytest.fixture
def sample_decisions():
    """Return sample decision data."""
    return [
        {
            "id": str(uuid4()),
            "trigger": "Need to choose a database",
            "context": "Building a new application with complex queries",
            "options": ["PostgreSQL", "MongoDB", "MySQL"],
            "decision": "Use PostgreSQL",
            "rationale": "Better for relational data and complex queries",
            "created_at": "2024-01-01T00:00:00Z",
            "entities": ["PostgreSQL", "MongoDB"],
        },
        {
            "id": str(uuid4()),
            "trigger": "Need to implement caching",
            "context": "Application performance is slow",
            "options": ["Redis", "Memcached", "In-memory"],
            "decision": "Use Redis",
            "rationale": "Redis provides better data structures and persistence",
            "created_at": "2024-01-02T00:00:00Z",
            "entities": ["Redis", "Memcached"],
        },
    ]


@pytest.fixture
def sample_decision():
    """Return a single sample decision."""
    return {
        "id": str(uuid4()),
        "trigger": "Choosing an API framework",
        "context": "Need a fast, modern Python web framework",
        "options": ["FastAPI", "Django", "Flask"],
        "decision": "FastAPI",
        "rationale": "Best performance and async support",
        "created_at": "2024-01-15T10:30:00Z",
    }


# ============================================================================
# Redis Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for rate limiting tests."""
    redis = AsyncMock()

    # Pipeline mock
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[None, 5, None, None])
    redis.pipeline = MagicMock(return_value=pipe)
    redis.zrem = AsyncMock()

    return redis


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Mock response"
    return response


@pytest.fixture
def mock_embedding_response():
    """Create a mock embedding API response."""
    response = MagicMock()
    response.data = [MagicMock()]
    response.data[0].embedding = [0.1] * 2048
    return response


# ============================================================================
# Validation Issue Fixtures
# ============================================================================


@pytest.fixture
def sample_validation_issues():
    """Return sample validation issues."""
    from services.validator import ValidationIssue, IssueType, IssueSeverity

    return [
        ValidationIssue(
            type=IssueType.CIRCULAR_DEPENDENCY,
            severity=IssueSeverity.ERROR,
            message="Circular dependency: A -> B -> A",
            affected_nodes=["id1", "id2"],
            suggested_action="Remove the cycle",
            details={"cycle": ["A", "B", "A"]},
        ),
        ValidationIssue(
            type=IssueType.ORPHAN_ENTITY,
            severity=IssueSeverity.WARNING,
            message="Orphan entity: Unused Technology",
            affected_nodes=["id3"],
            suggested_action="Link or delete",
        ),
    ]
