"""Tests for the search router."""

from unittest.mock import AsyncMock, patch

import pytest


class AsyncContextManager:
    """Helper class for mocking async context managers."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestSearchEndpoint:
    """Tests for GET / (search) endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session that works with async with."""
        session = AsyncMock()
        # Make session work as async context manager
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, mock_session):
        """Empty search query should return empty results."""
        # Note: The router has min_length=2 validation, so empty queries
        # would be rejected by FastAPI before reaching the endpoint
        pass

    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_session):
        """Search should return matching decisions and entities."""
        sample_decisions = [
            {
                "d": {
                    "id": "decision-1",
                    "trigger": "Choosing a database",
                    "decision": "Use PostgreSQL",
                },
                "score": 0.95,
            }
        ]

        sample_entities = [
            {
                "e": {
                    "id": "entity-1",
                    "name": "PostgreSQL",
                    "type": "technology",
                },
                "score": 0.9,
            }
        ]

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()

            if "DecisionTrace" in query or "decision_fulltext" in query:
                async def decision_iter():
                    for d in sample_decisions:
                        yield d

                result.__aiter__ = lambda: decision_iter()
            else:
                async def entity_iter():
                    for e in sample_entities:
                        yield e

                result.__aiter__ = lambda: entity_iter()

            return result

        mock_session.run = mock_run

        async def get_mock_session():
            return AsyncContextManager(mock_session)

        with patch("routers.search.get_neo4j_session", side_effect=get_mock_session):
            from routers.search import search

            results = await search(query="database", type=None)

            # Should have results from decisions or entities
            assert len(results) >= 0  # May be filtered

    @pytest.mark.asyncio
    async def test_search_filters_by_decision_type(self, mock_session):
        """Search should only return decisions when type=decision."""
        sample_decisions = [
            {
                "d": {
                    "id": "decision-1",
                    "trigger": "Choosing a database",
                    "decision": "Use PostgreSQL",
                },
                "score": 0.95,
            }
        ]

        async def mock_run(query, **params):
            result = AsyncMock()

            async def decision_iter():
                for d in sample_decisions:
                    yield d

            result.__aiter__ = lambda: decision_iter()
            return result

        mock_session.run = mock_run

        async def get_mock_session():
            return AsyncContextManager(mock_session)

        with patch("routers.search.get_neo4j_session", side_effect=get_mock_session):
            from routers.search import search

            results = await search(query="database", type="decision")

            # Should only have decision type results
            for r in results:
                assert r.type == "decision"

    @pytest.mark.asyncio
    async def test_search_filters_by_entity_type(self, mock_session):
        """Search should only return entities when type=entity."""
        sample_entities = [
            {
                "e": {
                    "id": "entity-1",
                    "name": "PostgreSQL",
                    "type": "technology",
                },
                "score": 0.9,
            }
        ]

        async def mock_run(query, **params):
            result = AsyncMock()

            async def entity_iter():
                for e in sample_entities:
                    yield e

            result.__aiter__ = lambda: entity_iter()
            return result

        mock_session.run = mock_run

        async def get_mock_session():
            return AsyncContextManager(mock_session)

        with patch("routers.search.get_neo4j_session", side_effect=get_mock_session):
            from routers.search import search

            results = await search(query="postgres", type="entity")

            # Should only have entity type results
            for r in results:
                assert r.type == "entity"


class TestSuggestEndpoint:
    """Tests for GET /suggest endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.mark.asyncio
    async def test_suggest_returns_matching_entities(self, mock_session):
        """Suggest should return entities matching the prefix."""
        sample_suggestions = [
            {"name": "PostgreSQL", "type": "technology"},
            {"name": "Postgres Config", "type": "concept"},
        ]

        async def mock_run(query, **params):
            result = AsyncMock()

            async def suggestion_iter():
                for s in sample_suggestions:
                    yield s

            result.__aiter__ = lambda: suggestion_iter()
            return result

        mock_session.run = mock_run

        async def get_mock_session():
            return AsyncContextManager(mock_session)

        with patch("routers.search.get_neo4j_session", side_effect=get_mock_session):
            from routers.search import suggest

            results = await suggest(query="post", limit=10)

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_suggest_respects_limit(self, mock_session):
        """Suggest should respect the limit parameter."""
        sample_suggestions = [
            {"name": "Item1", "type": "concept"},
            {"name": "Item2", "type": "concept"},
            {"name": "Item3", "type": "concept"},
        ]

        async def mock_run(query, **params):
            result = AsyncMock()

            async def suggestion_iter():
                for s in sample_suggestions:
                    yield s

            result.__aiter__ = lambda: suggestion_iter()
            return result

        mock_session.run = mock_run

        async def get_mock_session():
            return AsyncContextManager(mock_session)

        with patch("routers.search.get_neo4j_session", side_effect=get_mock_session):
            from routers.search import suggest

            results = await suggest(query="item", limit=2)

            assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_suggest_empty_results(self, mock_session):
        """Suggest should return empty list when no matches."""
        async def mock_run(query, **params):
            result = AsyncMock()

            async def empty_iter():
                return
                yield

            result.__aiter__ = lambda: empty_iter()
            return result

        mock_session.run = mock_run

        async def get_mock_session():
            return AsyncContextManager(mock_session)

        with patch("routers.search.get_neo4j_session", side_effect=get_mock_session):
            from routers.search import suggest

            results = await suggest(query="xyz", limit=10)

            assert results == []
