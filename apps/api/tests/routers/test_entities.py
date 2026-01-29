"""Tests for the entities router."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from routers.entities import router


class TestGetAllEntities:
    """Tests for GET / endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_entities(self):
        """Sample entity records."""
        return [
            {"id": str(uuid4()), "name": "PostgreSQL", "type": "technology"},
            {"id": str(uuid4()), "name": "Redis", "type": "technology"},
            {"id": str(uuid4()), "name": "Microservices", "type": "concept"},
        ]

    @pytest.mark.asyncio
    async def test_get_all_entities_returns_list(self, mock_session, sample_entities):
        """Should return a list of entities."""
        mock_result = AsyncMock()

        async def async_iter():
            for e in sample_entities:
                yield {"e": e}

        mock_result.__aiter__ = lambda: async_iter()
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.entities import get_all_entities

            results = await get_all_entities()
            assert len(results) == 3
            assert results[0].name == "PostgreSQL"

    @pytest.mark.asyncio
    async def test_get_all_entities_empty(self, mock_session):
        """Should return empty list when no entities."""
        mock_result = AsyncMock()

        async def empty_iter():
            return
            yield

        mock_result.__aiter__ = lambda: empty_iter()
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.entities import get_all_entities

            results = await get_all_entities()
            assert results == []


class TestGetEntity:
    """Tests for GET /{entity_id} endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_entity_found(self, mock_session):
        """Should return entity when found."""
        entity_id = str(uuid4())
        entity_data = {"id": entity_id, "name": "PostgreSQL", "type": "technology"}

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"e": entity_data})
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.entities import get_entity

            result = await get_entity(entity_id)
            assert result.id == entity_id
            assert result.name == "PostgreSQL"

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, mock_session):
        """Should raise 404 when entity not found."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from fastapi import HTTPException

            from routers.entities import get_entity

            with pytest.raises(HTTPException) as exc_info:
                await get_entity("nonexistent-id")
            assert exc_info.value.status_code == 404


class TestCreateEntity:
    """Tests for POST / endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_entity_success(self, mock_session):
        """Should create and return new entity."""
        mock_session.run = AsyncMock()

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from models.schemas import Entity

            from routers.entities import create_entity

            new_entity = Entity(name="NewTech", type="technology")
            result = await create_entity(new_entity)

            assert result.name == "NewTech"
            assert result.type == "technology"
            assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_entity_with_id(self, mock_session):
        """Should use provided ID when creating entity."""
        entity_id = str(uuid4())
        mock_session.run = AsyncMock()

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from models.schemas import Entity

            from routers.entities import create_entity

            new_entity = Entity(id=entity_id, name="NewTech", type="technology")
            result = await create_entity(new_entity)

            assert result.id == entity_id


class TestDeleteEntity:
    """Tests for DELETE /{entity_id} endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_delete_entity_success(self, mock_session):
        """Should delete entity when it exists."""
        entity_id = str(uuid4())
        entity_data = {"id": entity_id, "name": "OldTech", "type": "technology"}

        # First call checks existence, second checks relationships, third deletes
        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()
            if call_count[0] == 1:
                # Entity exists
                result.single = AsyncMock(return_value={"e": entity_data})
            elif call_count[0] == 2:
                # No relationships
                result.single = AsyncMock(return_value={"rel_count": 0})
            else:
                # Delete successful
                result.single = AsyncMock(return_value=None)
            return result

        mock_session.run = mock_run

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.entities import delete_entity

            result = await delete_entity(entity_id)
            assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_entity_not_found(self, mock_session):
        """Should raise 404 when entity doesn't exist."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from fastapi import HTTPException

            from routers.entities import delete_entity

            with pytest.raises(HTTPException) as exc_info:
                await delete_entity("nonexistent-id")
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entity_with_relationships_blocked(self, mock_session):
        """Should block delete when entity has relationships."""
        entity_id = str(uuid4())
        entity_data = {"id": entity_id, "name": "LinkedTech", "type": "technology"}

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()
            if call_count[0] == 1:
                result.single = AsyncMock(return_value={"e": entity_data})
            else:
                result.single = AsyncMock(return_value={"rel_count": 5})
            return result

        mock_session.run = mock_run

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from fastapi import HTTPException

            from routers.entities import delete_entity

            with pytest.raises(HTTPException) as exc_info:
                await delete_entity(entity_id, force=False)
            assert exc_info.value.status_code == 400
            assert "relationships" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_entity_force(self, mock_session):
        """Should force delete entity with relationships."""
        entity_id = str(uuid4())
        entity_data = {"id": entity_id, "name": "LinkedTech", "type": "technology"}

        call_count = [0]

        async def mock_run(query, **params):
            call_count[0] += 1
            result = AsyncMock()
            if call_count[0] == 1:
                result.single = AsyncMock(return_value={"e": entity_data})
            else:
                result.single = AsyncMock(return_value=None)
            return result

        mock_session.run = mock_run

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from routers.entities import delete_entity

            result = await delete_entity(entity_id, force=True)
            assert result["status"] == "deleted"


class TestLinkEntity:
    """Tests for POST /link endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_link_entity_success(self, mock_session):
        """Should link entity to decision."""
        mock_session.run = AsyncMock()

        with patch(
            "routers.entities.get_neo4j_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            from models.schemas import LinkEntityRequest

            from routers.entities import link_entity

            request = LinkEntityRequest(
                decision_id="decision-1",
                entity_id="entity-1",
                relationship="uses",
            )
            result = await link_entity(request)
            assert result["status"] == "linked"
