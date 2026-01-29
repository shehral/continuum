"""Tests for the dashboard router."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


class TestGetDashboardStats:
    """Tests for GET /stats endpoint."""

    @pytest.fixture
    def mock_neo4j_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_postgres_session(self):
        """Create a mock PostgreSQL session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_success(
        self, mock_neo4j_session, mock_postgres_session
    ):
        """Should return dashboard statistics."""
        # Mock PostgreSQL session count
        mock_pg_result = AsyncMock()
        mock_pg_result.scalar = AsyncMock(return_value=15)
        mock_postgres_session.execute = AsyncMock(return_value=mock_pg_result)

        # Mock Neo4j decision count
        decision_result = AsyncMock()
        decision_result.single = AsyncMock(
            return_value={"total_decisions": 25, "total_entities": 50}
        )

        # Mock Neo4j recent decisions
        recent_decisions = [
            {
                "d": {
                    "id": str(uuid4()),
                    "trigger": "Recent decision 1",
                    "decision": "Choice 1",
                    "created_at": "2024-01-15T00:00:00Z",
                    "source": "manual",
                },
                "entity_names": ["Entity1"],
            },
            {
                "d": {
                    "id": str(uuid4()),
                    "trigger": "Recent decision 2",
                    "decision": "Choice 2",
                    "created_at": "2024-01-14T00:00:00Z",
                    "source": "interview",
                },
                "entity_names": [],
            },
        ]

        recent_result = AsyncMock()

        async def async_iter():
            for d in recent_decisions:
                yield d

        recent_result.__aiter__ = lambda: async_iter()

        call_count = [0]

        async def mock_neo4j_run(query, **params):
            call_count[0] += 1
            if "count(d)" in query.lower():
                return decision_result
            else:
                return recent_result

        mock_neo4j_session.run = mock_neo4j_run

        with patch(
            "routers.dashboard.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_neo4j_session,
        ), patch(
            "routers.dashboard.get_db",
            return_value=mock_postgres_session,
        ):
            from routers.dashboard import get_dashboard_stats

            result = await get_dashboard_stats(db=mock_postgres_session)

            assert result.total_decisions == 25
            assert result.total_entities == 50
            assert result.total_sessions == 15
            assert len(result.recent_decisions) == 2

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_empty(
        self, mock_neo4j_session, mock_postgres_session
    ):
        """Should return zeros when database is empty."""
        # Mock PostgreSQL session count
        mock_pg_result = AsyncMock()
        mock_pg_result.scalar = AsyncMock(return_value=0)
        mock_postgres_session.execute = AsyncMock(return_value=mock_pg_result)

        # Mock Neo4j empty response
        empty_result = AsyncMock()
        empty_result.single = AsyncMock(
            return_value={"total_decisions": 0, "total_entities": 0}
        )

        recent_result = AsyncMock()

        async def empty_iter():
            return
            yield

        recent_result.__aiter__ = lambda: empty_iter()

        call_count = [0]

        async def mock_neo4j_run(query, **params):
            call_count[0] += 1
            if "count(d)" in query.lower():
                return empty_result
            else:
                return recent_result

        mock_neo4j_session.run = mock_neo4j_run

        with patch(
            "routers.dashboard.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_neo4j_session,
        ):
            from routers.dashboard import get_dashboard_stats

            result = await get_dashboard_stats(db=mock_postgres_session)

            assert result.total_decisions == 0
            assert result.total_entities == 0
            assert result.total_sessions == 0
            assert result.recent_decisions == []

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_null_session_count(
        self, mock_neo4j_session, mock_postgres_session
    ):
        """Should handle null session count gracefully."""
        # Mock PostgreSQL returning None
        mock_pg_result = AsyncMock()
        mock_pg_result.scalar = AsyncMock(return_value=None)
        mock_postgres_session.execute = AsyncMock(return_value=mock_pg_result)

        # Mock Neo4j
        empty_result = AsyncMock()
        empty_result.single = AsyncMock(
            return_value={"total_decisions": 5, "total_entities": 10}
        )

        recent_result = AsyncMock()

        async def empty_iter():
            return
            yield

        recent_result.__aiter__ = lambda: empty_iter()

        async def mock_neo4j_run(query, **params):
            if "count(d)" in query.lower():
                return empty_result
            else:
                return recent_result

        mock_neo4j_session.run = mock_neo4j_run

        with patch(
            "routers.dashboard.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_neo4j_session,
        ):
            from routers.dashboard import get_dashboard_stats

            result = await get_dashboard_stats(db=mock_postgres_session)

            # Should default to 0 when None
            assert result.total_sessions == 0


class TestRecentDecisions:
    """Tests for recent decisions in dashboard stats."""

    @pytest.fixture
    def mock_neo4j_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def mock_postgres_session(self):
        """Create a mock PostgreSQL session."""
        session = AsyncMock()
        mock_pg_result = AsyncMock()
        mock_pg_result.scalar = AsyncMock(return_value=0)
        session.execute = AsyncMock(return_value=mock_pg_result)
        return session

    @pytest.mark.asyncio
    async def test_recent_decisions_ordered_by_date(
        self, mock_neo4j_session, mock_postgres_session
    ):
        """Recent decisions should be ordered by creation date."""
        recent_decisions = [
            {
                "d": {
                    "id": "1",
                    "trigger": "Newest",
                    "decision": "A",
                    "created_at": "2024-01-20T00:00:00Z",
                    "source": "manual",
                },
                "entity_names": [],
            },
            {
                "d": {
                    "id": "2",
                    "trigger": "Older",
                    "decision": "B",
                    "created_at": "2024-01-10T00:00:00Z",
                    "source": "manual",
                },
                "entity_names": [],
            },
        ]

        count_result = AsyncMock()
        count_result.single = AsyncMock(
            return_value={"total_decisions": 2, "total_entities": 0}
        )

        recent_result = AsyncMock()

        async def async_iter():
            for d in recent_decisions:
                yield d

        recent_result.__aiter__ = lambda: async_iter()

        async def mock_run(query, **params):
            if "count(d)" in query.lower():
                return count_result
            else:
                return recent_result

        mock_neo4j_session.run = mock_run

        with patch(
            "routers.dashboard.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_neo4j_session,
        ):
            from routers.dashboard import get_dashboard_stats

            result = await get_dashboard_stats(db=mock_postgres_session)

            assert len(result.recent_decisions) == 2
            # First should be the newest
            assert result.recent_decisions[0].trigger == "Newest"
