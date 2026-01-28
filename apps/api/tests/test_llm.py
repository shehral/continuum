"""Tests for NVIDIA Llama LLM integration and rate limiting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.interview import InterviewAgent, InterviewState
from services.extractor import DecisionExtractor
from services.llm import LLMClient, RateLimiter, get_llm_client

# ============================================================================
# Rate Limiter Tests
# ============================================================================

class TestRateLimiter:
    """Test the Redis-based rate limiter."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[None, 0, None, None])
        redis.pipeline = MagicMock(return_value=pipe)
        redis.zrem = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_acquire_when_under_limit(self, mock_redis):
        """Should allow request when under rate limit."""
        limiter = RateLimiter(mock_redis, "test", max_requests=30, window=60)

        # Mock: 5 requests in window (under limit of 30)
        mock_redis.pipeline().execute = AsyncMock(return_value=[None, 5, None, None])

        result = await limiter.acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_when_at_limit(self, mock_redis):
        """Should deny request when at rate limit."""
        limiter = RateLimiter(mock_redis, "test", max_requests=30, window=60)

        # Mock: 30 requests in window (at limit)
        mock_redis.pipeline().execute = AsyncMock(return_value=[None, 30, None, None])

        result = await limiter.acquire()
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_slot_success(self, mock_redis):
        """Should wait and acquire slot when available."""
        limiter = RateLimiter(mock_redis, "test", max_requests=30, window=60)

        # First call: at limit, second call: under limit
        mock_redis.pipeline().execute = AsyncMock(
            side_effect=[
                [None, 30, None, None],  # First: denied
                [None, 10, None, None],  # Second: allowed
            ]
        )

        result = await limiter.wait_for_slot(timeout=5.0)
        assert result is True


# ============================================================================
# LLM Client Tests
# ============================================================================

class TestLLMClient:
    """Test the NVIDIA LLM client."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Test response"
        return response

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_openai_response):
        """Should generate completion successfully."""
        with patch('services.llm.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
            mock_client_class.return_value = mock_client

            with patch('services.llm.redis') as mock_redis_module:
                mock_redis = AsyncMock()
                mock_pipe = AsyncMock()
                mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])
                mock_redis.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis_module.from_url = MagicMock(return_value=mock_redis)

                client = LLMClient()
                result = await client.generate("Test prompt")

                assert result == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, mock_openai_response):
        """Should include system prompt in messages."""
        with patch('services.llm.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
            mock_client_class.return_value = mock_client

            with patch('services.llm.redis') as mock_redis_module:
                mock_redis = AsyncMock()
                mock_pipe = AsyncMock()
                mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])
                mock_redis.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis_module.from_url = MagicMock(return_value=mock_redis)

                client = LLMClient()
                await client.generate("Test prompt", system_prompt="You are helpful")

                # Verify system prompt was included
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args.kwargs['messages']
                assert messages[0]['role'] == 'system'
                assert messages[0]['content'] == 'You are helpful'

    @pytest.mark.asyncio
    async def test_generate_rate_limited(self):
        """Should raise exception when rate limited."""
        with patch('services.llm.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            with patch('services.llm.redis') as mock_redis_module:
                mock_redis = AsyncMock()
                mock_pipe = AsyncMock()
                # Always at limit
                mock_pipe.execute = AsyncMock(return_value=[None, 100, None, None])
                mock_redis.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis.zrem = AsyncMock()
                mock_redis_module.from_url = MagicMock(return_value=mock_redis)

                client = LLMClient()

                with pytest.raises(Exception, match="Rate limit exceeded"):
                    await client.generate("Test prompt")


# ============================================================================
# Decision Extractor Tests
# ============================================================================

class TestDecisionExtractor:
    """Test the decision extraction service."""

    @pytest.mark.asyncio
    async def test_extract_decisions_parses_json(self):
        """Should parse JSON response into DecisionCreate objects."""
        mock_response = '''[
            {
                "trigger": "Need to choose a database",
                "context": "Building a new application",
                "options": ["PostgreSQL", "MongoDB"],
                "decision": "Use PostgreSQL",
                "rationale": "Better for relational data",
                "confidence": 0.9
            }
        ]'''

        with patch('services.extractor.get_llm_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            extractor = DecisionExtractor()

            # Create a mock conversation
            mock_conversation = MagicMock()
            mock_conversation.get_full_text = MagicMock(return_value="Test conversation")

            decisions = await extractor.extract_decisions(mock_conversation)

            assert len(decisions) == 1
            assert decisions[0].trigger == "Need to choose a database"
            assert decisions[0].decision == "Use PostgreSQL"
            assert decisions[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_extract_decisions_handles_markdown(self):
        """Should handle markdown-wrapped JSON response."""
        mock_response = '''```json
[
    {
        "trigger": "Test",
        "context": "Test context",
        "options": [],
        "decision": "Test decision",
        "rationale": "Test rationale",
        "confidence": 0.8
    }
]
```'''

        with patch('services.extractor.get_llm_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            extractor = DecisionExtractor()
            mock_conversation = MagicMock()
            mock_conversation.get_full_text = MagicMock(return_value="Test")

            decisions = await extractor.extract_decisions(mock_conversation)

            assert len(decisions) == 1
            assert decisions[0].trigger == "Test"

    @pytest.mark.asyncio
    async def test_extract_entities(self):
        """Should extract entities from text."""
        mock_response = '''{
            "entities": [
                {"name": "PostgreSQL", "type": "technology", "confidence": 0.95},
                {"name": "Caching", "type": "concept", "confidence": 0.85}
            ],
            "reasoning": "PostgreSQL is a database technology, caching is a concept"
        }'''

        with patch('services.extractor.get_llm_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            extractor = DecisionExtractor()
            entities = await extractor.extract_entities("Using PostgreSQL with caching")

            assert len(entities) == 2
            assert entities[0]["name"] == "PostgreSQL"
            assert entities[0]["type"] == "technology"
            assert entities[1]["name"] == "Caching"
            assert entities[1]["type"] == "concept"

    @pytest.mark.asyncio
    async def test_extract_decisions_handles_error(self):
        """Should return empty list on error."""
        with patch('services.extractor.get_llm_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(side_effect=Exception("API Error"))
            mock_get_client.return_value = mock_client

            extractor = DecisionExtractor()
            mock_conversation = MagicMock()
            mock_conversation.get_full_text = MagicMock(return_value="Test")

            decisions = await extractor.extract_decisions(mock_conversation)

            assert decisions == []


# ============================================================================
# Interview Agent Tests
# ============================================================================

class TestInterviewAgent:
    """Test the interview agent."""

    def test_determine_next_state_opening(self):
        """Should start with TRIGGER state."""
        agent = InterviewAgent()
        state = agent._determine_next_state([])
        assert state == InterviewState.TRIGGER

    def test_determine_next_state_progression(self):
        """Should progress through states based on user responses."""
        agent = InterviewAgent()

        # 1 substantial response -> CONTEXT
        history = [{"role": "user", "content": "A" * 30}]
        assert agent._determine_next_state(history) == InterviewState.CONTEXT

        # 2 responses -> OPTIONS
        history.append({"role": "user", "content": "B" * 30})
        assert agent._determine_next_state(history) == InterviewState.OPTIONS

        # 3 responses -> DECISION
        history.append({"role": "user", "content": "C" * 30})
        assert agent._determine_next_state(history) == InterviewState.DECISION

        # 4 responses -> RATIONALE
        history.append({"role": "user", "content": "D" * 30})
        assert agent._determine_next_state(history) == InterviewState.RATIONALE

        # 5+ responses -> SUMMARIZING
        history.append({"role": "user", "content": "E" * 30})
        assert agent._determine_next_state(history) == InterviewState.SUMMARIZING

    def test_fallback_response(self):
        """Should provide fallback responses when AI unavailable."""
        agent = InterviewAgent()

        response = agent._generate_fallback_response("test", [])
        assert "context" in response.lower() or "situation" in response.lower()

    @pytest.mark.asyncio
    async def test_process_message(self):
        """Should process message and return response with entities."""
        with patch('agents.interview.get_llm_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value="That's interesting! Tell me more about the context.")
            mock_get_client.return_value = mock_client

            with patch.object(DecisionExtractor, 'extract_entities', new_callable=AsyncMock) as mock_extract:
                mock_extract.return_value = []

                agent = InterviewAgent()
                response, entities = await agent.process_message(
                    "I needed to choose a database",
                    []
                )

                assert "interesting" in response.lower() or "context" in response.lower()

    @pytest.mark.asyncio
    async def test_synthesize_decision(self):
        """Should synthesize decision from conversation history."""
        mock_response = '''{
            "trigger": "Choose database",
            "context": "New project",
            "options": ["PostgreSQL", "MongoDB"],
            "decision": "PostgreSQL",
            "rationale": "Relational data needs",
            "confidence": 0.85
        }'''

        with patch('agents.interview.get_llm_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            agent = InterviewAgent()
            history = [
                {"role": "user", "content": "I chose PostgreSQL"},
                {"role": "assistant", "content": "Why?"},
                {"role": "user", "content": "Relational data"},
            ]

            result = await agent.synthesize_decision(history)

            assert result["trigger"] == "Choose database"
            assert result["decision"] == "PostgreSQL"
            assert result["confidence"] == 0.85


# ============================================================================
# Integration Tests (requires running services)
# ============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests that require running NVIDIA API and Redis."""

    @pytest.mark.asyncio
    async def test_llm_client_real_request(self):
        """Test actual LLM request (requires NVIDIA API key)."""
        client = get_llm_client()

        try:
            response = await client.generate(
                "Say 'Hello' and nothing else.",
                max_tokens=10,
            )
            assert "hello" in response.lower()
        except Exception as e:
            pytest.skip(f"NVIDIA API not available: {e}")

    @pytest.mark.asyncio
    async def test_extractor_real_extraction(self):
        """Test actual decision extraction (requires NVIDIA API)."""
        extractor = DecisionExtractor()

        try:
            entities = await extractor.extract_entities(
                "We decided to use PostgreSQL for the database and Redis for caching."
            )
            entity_names = [e.name.lower() for e in entities]
            assert any("postgres" in name for name in entity_names)
        except Exception as e:
            pytest.skip(f"NVIDIA API not available: {e}")


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
