"""Tests for the decisions router."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


class TestGetDecisions:
    """Tests for GET / endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_decisions(self):
        """Sample decision records."""
        return [
            {
                "d": {
                    "id": str(uuid4()),
                    "trigger": "Choosing a database",
                    "context": "Need relational database",
                    "options": ["PostgreSQL", "MySQL"],
                    "decision": "PostgreSQL",
                    "rationale": "Better for complex queries",
                    "confidence": 0.9,
                    "created_at": "2024-01-01T00:00:00Z",
                    "source": "manual",
                },
                "entities": [
                    {"id": str(uuid4()), "name": "PostgreSQL", "type": "technology"}
                ],
            },
            {
                "d": {
                    "id": str(uuid4()),
                    "trigger": "Selecting caching",
                    "context": "Need fast cache",
                    "options": ["Redis", "Memcached"],
                    "decision": "Redis",
                    "rationale": "Better data structures",
                    "confidence": 0.85,
                    "created_at": "2024-01-02T00:00:00Z",
                    "source": "interview",
                },
                "entities": [],
            },
        ]

    @pytest.mark.asyncio
    async def test_get_decisions_returns_list(self, mock_session, sample_decisions):
        """Should return a list of decisions."""
        mock_result = AsyncMock()

        async def async_iter():
            for d in sample_decisions:
                yield d

        mock_result.__aiter__ = lambda: async_iter()
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.decisions import get_decisions

            results = await get_decisions(limit=50, offset=0)
            assert len(results) == 2
            assert results[0].trigger == "Choosing a database"

    @pytest.mark.asyncio
    async def test_get_decisions_empty(self, mock_session):
        """Should return empty list when no decisions."""
        mock_result = AsyncMock()

        async def empty_iter():
            return
            yield

        mock_result.__aiter__ = lambda: empty_iter()
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.decisions import get_decisions

            results = await get_decisions(limit=50, offset=0)
            assert results == []

    @pytest.mark.asyncio
    async def test_get_decisions_with_pagination(self, mock_session):
        """Should pass pagination parameters to query."""
        mock_result = AsyncMock()

        async def empty_iter():
            return
            yield

        mock_result.__aiter__ = lambda: empty_iter()
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.decisions import get_decisions

            await get_decisions(limit=10, offset=20)

            # Verify query was called with pagination params
            call_args = mock_session.run.call_args
            assert call_args[1]["limit"] == 10
            assert call_args[1]["offset"] == 20


class TestGetDecision:
    """Tests for GET /{decision_id} endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_decision_found(self, mock_session):
        """Should return decision when found."""
        decision_id = str(uuid4())
        decision_data = {
            "d": {
                "id": decision_id,
                "trigger": "Test decision",
                "context": "Test context",
                "options": ["A", "B"],
                "decision": "A",
                "rationale": "Because",
                "confidence": 0.9,
                "created_at": "2024-01-01T00:00:00Z",
                "source": "manual",
            },
            "entities": [],
        }

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=decision_data)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.decisions import get_decision

            result = await get_decision(decision_id)
            assert result.id == decision_id
            assert result.trigger == "Test decision"

    @pytest.mark.asyncio
    async def test_get_decision_not_found(self, mock_session):
        """Should raise 404 when decision not found."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from fastapi import HTTPException

            from routers.decisions import get_decision

            with pytest.raises(HTTPException) as exc_info:
                await get_decision("nonexistent-id")
            assert exc_info.value.status_code == 404


class TestDeleteDecision:
    """Tests for DELETE /{decision_id} endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_delete_decision_success(self, mock_session):
        """Should delete decision when it exists."""
        decision_id = str(uuid4())
        decision_data = {"d": {"id": decision_id}}

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
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.decisions import delete_decision

            result = await delete_decision(decision_id)
            assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_decision_not_found(self, mock_session):
        """Should raise 404 when decision doesn't exist."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from fastapi import HTTPException

            from routers.decisions import delete_decision

            with pytest.raises(HTTPException) as exc_info:
                await delete_decision("nonexistent-id")
            assert exc_info.value.status_code == 404


class TestCreateDecision:
    """Tests for POST / endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_decision_manual(self, mock_session):
        """Should create decision without auto-extraction."""
        decision_id = str(uuid4())

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()
            if "RETURN d, entities" in query:
                result.single = AsyncMock(
                    return_value={
                        "d": {
                            "id": decision_id,
                            "trigger": "Test",
                            "context": "Context",
                            "options": ["A"],
                            "decision": "A",
                            "rationale": "Because",
                            "confidence": 1.0,
                            "created_at": "2024-01-01T00:00:00Z",
                            "source": "manual",
                        },
                        "entities": [],
                    }
                )
            else:
                result.single = AsyncMock(return_value=None)
            return result

        mock_session.run = mock_run

        with patch(
            "routers.decisions.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.decisions import ManualDecisionInput, create_decision

            input_data = ManualDecisionInput(
                trigger="Test",
                context="Context",
                options=["A"],
                decision="A",
                rationale="Because",
                auto_extract=False,
            )
            result = await create_decision(input_data)
            assert result.trigger == "Test"
            assert result.source == "manual"
