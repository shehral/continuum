"""Tests for the graph router."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_async_result_mock(records):
    """Create a mock Neo4j result that works as an async iterator."""
    result = MagicMock()

    async def async_iter():
        for r in records:
            yield r

    result.__aiter__ = lambda self: async_iter()
    return result


def create_neo4j_session_mock():
    """Create a mock Neo4j session that works as an async context manager."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


class TestGetGraph:
    """Tests for GET / endpoint."""

    @pytest.fixture
    def sample_decisions(self):
        """Sample decision nodes."""
        return [
            {
                "d": {
                    "id": str(uuid4()),
                    "trigger": "Choosing database",
                    "context": "Need fast queries",
                    "options": ["PostgreSQL", "MySQL"],
                    "decision": "PostgreSQL",
                    "rationale": "Better performance",
                    "confidence": 0.9,
                    "created_at": "2024-01-01T00:00:00Z",
                    "source": "manual",
                },
                "has_embedding": True,
            }
        ]

    @pytest.fixture
    def sample_entities(self):
        """Sample entity nodes."""
        return [
            {
                "e": {
                    "id": str(uuid4()),
                    "name": "PostgreSQL",
                    "type": "technology",
                    "aliases": [],
                },
                "has_embedding": True,
            }
        ]

    @pytest.fixture
    def sample_edges(self):
        """Sample graph edges."""
        return [
            {
                "source": "decision-1",
                "target": "entity-1",
                "relationship": "INVOLVES",
                "weight": 1.0,
                "score": None,
                "confidence": None,
                "shared_entities": None,
                "reasoning": None,
            }
        ]

    @pytest.mark.asyncio
    async def test_get_graph_returns_nodes_and_edges(
        self, sample_decisions, sample_entities, sample_edges
    ):
        """Should return graph with nodes and edges."""
        mock_session = create_neo4j_session_mock()

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            if "DecisionTrace" in query and "Entity" not in query:
                return create_async_result_mock(sample_decisions)
            elif "Entity" in query and "DecisionTrace" not in query:
                return create_async_result_mock(sample_entities)
            else:
                return create_async_result_mock(sample_edges)

        mock_session.run = mock_run

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_graph

            result = await get_graph()

            assert len(result.nodes) >= 1
            assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_get_graph_empty(self):
        """Should return empty graph when database is empty."""
        mock_session = create_neo4j_session_mock()
        mock_session.run = AsyncMock(return_value=create_async_result_mock([]))

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_graph

            result = await get_graph()

            assert result.nodes == []
            assert result.edges == []

    @pytest.mark.asyncio
    async def test_get_graph_filters_by_source(
        self, sample_decisions, sample_entities, sample_edges
    ):
        """Should filter by source when specified."""
        mock_session = create_neo4j_session_mock()

        queries_called = []

        async def mock_run(query, **params):
            queries_called.append(query)
            # Return appropriate data based on query
            if "DecisionTrace" in query and "Entity" not in query:
                return create_async_result_mock(sample_decisions)
            elif "Entity" in query and "DecisionTrace" not in query:
                return create_async_result_mock(sample_entities)
            else:
                return create_async_result_mock(sample_edges)

        mock_session.run = mock_run

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_graph

            await get_graph(source_filter="manual")

            # Verify at least one query includes source filter
            assert any("source" in q.lower() for q in queries_called)


class TestGetNodeDetails:
    """Tests for GET /nodes/{node_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_decision_node(self):
        """Should return decision node details."""
        mock_session = create_neo4j_session_mock()
        node_id = str(uuid4())
        decision_data = {
            "d": {
                "id": node_id,
                "trigger": "Test decision",
                "context": "Test context",
                "options": ["A", "B"],
                "decision": "A",
                "rationale": "Because",
                "confidence": 0.9,
                "created_at": "2024-01-01T00:00:00Z",
            },
            "entities": ["PostgreSQL"],
            "supersedes": [],
            "conflicts_with": [],
            "has_embedding": True,
        }

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()
            if call_count[0] == 1:
                result.single = AsyncMock(return_value=decision_data)
            else:
                result.single = AsyncMock(return_value=None)
            return result

        mock_session.run = mock_run

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_node_details

            result = await get_node_details(node_id)

            assert result.id == node_id
            assert result.type == "decision"

    @pytest.mark.asyncio
    async def test_get_entity_node(self):
        """Should return entity node details."""
        mock_session = create_neo4j_session_mock()
        node_id = str(uuid4())
        entity_data = {
            "e": {
                "id": node_id,
                "name": "PostgreSQL",
                "type": "technology",
                "aliases": ["postgres", "pg"],
            },
            "decisions": ["Choosing a database"],
            "related_entities": [],
            "has_embedding": True,
        }

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()
            if call_count[0] == 1:
                # First query for decision fails
                result.single = AsyncMock(return_value=None)
            else:
                # Second query for entity succeeds
                result.single = AsyncMock(return_value=entity_data)
            return result

        mock_session.run = mock_run

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_node_details

            result = await get_node_details(node_id)

            assert result.id == node_id
            assert result.type == "entity"

    @pytest.mark.asyncio
    async def test_get_node_not_found(self):
        """Should raise 404 when node not found."""
        mock_session = create_neo4j_session_mock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from fastapi import HTTPException

            from routers.graph import get_node_details

            with pytest.raises(HTTPException) as exc_info:
                await get_node_details("nonexistent-id")
            assert exc_info.value.status_code == 404


class TestResetGraph:
    """Tests for DELETE /reset endpoint."""

    @pytest.mark.asyncio
    async def test_reset_requires_confirmation(self):
        """Should abort without confirmation."""
        mock_session = create_neo4j_session_mock()

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import reset_graph

            result = await reset_graph(confirm=False)

            assert result["status"] == "aborted"
            # Should not have called any Neo4j operations
            assert mock_session.run.call_count == 0

    @pytest.mark.asyncio
    async def test_reset_with_confirmation(self):
        """Should delete all data with confirmation."""
        mock_session = create_neo4j_session_mock()
        mock_session.run = AsyncMock()

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import reset_graph

            result = await reset_graph(confirm=True)

            assert result["status"] == "completed"
            # Should have called delete for relationships and nodes
            assert mock_session.run.call_count == 2


class TestGetGraphStats:
    """Tests for GET /stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Should return graph statistics."""
        mock_session = create_neo4j_session_mock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(
            return_value={
                "total_decisions": 25,
                "decisions_with_embeddings": 20,
                "total_entities": 50,
                "entities_with_embeddings": 45,
                "total_relationships": 100,
            }
        )
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_graph_stats

            result = await get_graph_stats()

            assert result["decisions"]["total"] == 25
            assert result["decisions"]["with_embeddings"] == 20
            assert result["entities"]["total"] == 50
            assert result["relationships"] == 100

    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        """Should return zeros when database is empty."""
        mock_session = create_neo4j_session_mock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.graph.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.graph import get_graph_stats

            result = await get_graph_stats()

            assert result["decisions"]["total"] == 0
            assert result["entities"]["total"] == 0
            assert result["relationships"] == 0
