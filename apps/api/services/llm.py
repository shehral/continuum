"""LLM client for NVIDIA NIM API with per-user rate limiting, retry logic, request size validation, and model fallback.

SEC-009: Implements per-user rate limiting instead of global rate limiting.
ML-QW-2: Model fallback support - if primary model fails, automatically fall back to secondary model.
"""

import asyncio
import random
import re
import time
from typing import AsyncIterator

import redis.asyncio as redis
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)


def strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> tags from model output."""
    # Remove thinking blocks
    text = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
    return text.strip()


# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Overhead tokens for message formatting (role labels, special tokens, etc.)
MESSAGE_OVERHEAD_TOKENS = 10

# Default rate limits (SEC-009)
DEFAULT_RATE_LIMIT_REQUESTS = 30  # Per minute for authenticated users
DEFAULT_RATE_LIMIT_WINDOW = 60  # Window in seconds
ANONYMOUS_RATE_LIMIT_REQUESTS = 10  # Stricter limit for anonymous users


class PromptTooLargeError(ValueError):
    """Raised when the prompt exceeds the maximum allowed token count."""

    def __init__(self, estimated_tokens: int, max_tokens: int, message: str | None = None):
        self.estimated_tokens = estimated_tokens
        self.max_tokens = max_tokens
        if message is None:
            message = (
                f"Prompt too large: estimated {estimated_tokens} tokens, "
                f"max allowed is {max_tokens} tokens"
            )
        super().__init__(message)


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded (SEC-009)."""

    def __init__(self, user_id: str, retry_after: float = 30.0):
        self.user_id = user_id
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for user. Please retry after {retry_after:.0f} seconds."
        )


class RateLimiter:
    """Token bucket rate limiter using Redis with per-user support (SEC-009).

    Supports both per-user and global rate limiting:
    - Per-user: Uses key format 'ratelimit:user:{user_id}:nvidia_api'
    - Global: Uses key format 'ratelimit:global:nvidia_api'

    Anonymous users get stricter rate limits than authenticated users.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        user_id: str | None = None,
        max_requests: int | None = None,
        window: int | None = None,
    ):
        """Initialize rate limiter.

        Args:
            redis_client: Redis async client
            user_id: User ID for per-user limiting. If None or "anonymous",
                     uses stricter anonymous limits.
            max_requests: Max requests per window. Defaults based on user type.
            window: Window size in seconds.
        """
        self.redis = redis_client
        self.user_id = user_id or "anonymous"

        # Set window (default 60 seconds)
        settings = get_settings()
        self.window = window or settings.rate_limit_window

        # Determine rate limit based on user type (SEC-009)
        if self.user_id == "anonymous":
            self.max_requests = max_requests or ANONYMOUS_RATE_LIMIT_REQUESTS
            self.key = "ratelimit:anonymous:nvidia_api"
        else:
            self.max_requests = max_requests or settings.rate_limit_requests
            # Per-user key format for isolation
            self.key = f"ratelimit:user:{self.user_id}:nvidia_api"

        logger.debug(
            f"Rate limiter initialized: user={self.user_id[:8]}..., "
            f"limit={self.max_requests}/{self.window}s"
        )

    async def acquire(self) -> bool:
        """Try to acquire a rate limit token. Returns True if allowed."""
        now = time.time()
        window_start = now - self.window

        pipe = self.redis.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(self.key, 0, window_start)
        # Count current entries
        pipe.zcard(self.key)
        # Add new entry
        pipe.zadd(self.key, {str(now): now})
        # Set expiry
        pipe.expire(self.key, self.window)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= self.max_requests:
            # Remove the entry we just added
            await self.redis.zrem(self.key, str(now))
            logger.warning(
                f"Rate limit exceeded: user={self.user_id[:8] if len(self.user_id) > 8 else self.user_id}, "
                f"count={current_count}/{self.max_requests}"
            )
            return False
        return True

    async def get_remaining(self) -> tuple[int, float]:
        """Get remaining requests and time until window reset.

        Returns:
            Tuple of (remaining_requests, seconds_until_reset)
        """
        now = time.time()
        window_start = now - self.window

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(self.key, 0, window_start)
        pipe.zcard(self.key)
        pipe.zrange(self.key, 0, 0, withscores=True)

        results = await pipe.execute()
        current_count = results[1]
        oldest_entry = results[2]

        remaining = max(0, self.max_requests - current_count)

        # Calculate time until oldest entry expires
        if oldest_entry:
            oldest_time = oldest_entry[0][1]
            seconds_until_reset = max(0, oldest_time + self.window - now)
        else:
            seconds_until_reset = 0

        return remaining, seconds_until_reset

    async def wait_for_slot(self, timeout: float = 30.0) -> bool:
        """Wait until a rate limit slot is available."""
        start = time.time()
        while time.time() - start < timeout:
            if await self.acquire():
                return True
            await asyncio.sleep(0.5)
        return False


class LLMClient:
    """Client for NVIDIA NIM Llama API with per-user rate limiting, retry logic, size validation, and model fallback.

    Features:
    - Per-user token bucket rate limiting via Redis (SEC-009)
    - Different limits for authenticated vs anonymous users
    - Exponential backoff with jitter for transient failures
    - Retries on 429, 500, 502, 503, 504 status codes
    - Thinking tag stripping from model output
    - Request size validation to prevent oversized prompts (ML-P1-3)
    - Model fallback support (ML-QW-2): Falls back to secondary model if primary fails
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self.settings.get_nvidia_api_key(),
        )
        self.model = self.settings.nvidia_model
        # ML-QW-2: Fallback model configuration
        self.fallback_model = self.settings.llm_fallback_model
        self.fallback_enabled = self.settings.llm_fallback_enabled
        self._redis: redis.Redis | None = None
        # Cache rate limiters by user_id to avoid recreating
        self._rate_limiters: dict[str, RateLimiter] = {}

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url)
        return self._redis

    async def _get_rate_limiter(self, user_id: str | None = None) -> RateLimiter:
        """Get or create rate limiter for a specific user (SEC-009).

        Args:
            user_id: User ID for per-user rate limiting.
                     If None, uses global rate limiting.

        Returns:
            RateLimiter instance for the user
        """
        key = user_id or "anonymous"

        if key not in self._rate_limiters:
            redis_client = await self._get_redis()
            self._rate_limiters[key] = RateLimiter(
                redis_client,
                user_id=user_id,
                max_requests=self.settings.rate_limit_requests,
                window=self.settings.rate_limit_window,
            )

        return self._rate_limiters[key]

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a piece of text.

        Uses a simple heuristic: approximately 4 characters per token for English text.
        This is a conservative estimate that works well for most LLMs including Llama.

        Note: For more accurate counting, consider using tiktoken or the model's
        actual tokenizer, but this adds latency and dependencies.

        Args:
            text: The text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Rough estimate: 4 characters per token (conservative for English)
        # This is faster than actual tokenization and sufficient for pre-flight checks
        return len(text) // 4 + 1

    def _estimate_messages_tokens(self, messages: list[dict]) -> int:
        """Estimate total tokens for a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Estimated total token count including message overhead
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self._estimate_tokens(content)
            # Add overhead for role label and message formatting
            total += MESSAGE_OVERHEAD_TOKENS
        return total

    def _validate_prompt_size(
        self,
        prompt: str,
        system_prompt: str = "",
        max_prompt_tokens: int | None = None,
    ) -> int:
        """Validate that the prompt size is within limits.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_prompt_tokens: Override for max token limit (default: from settings)

        Returns:
            Estimated token count

        Raises:
            PromptTooLargeError: If estimated tokens exceed the limit
        """
        if max_prompt_tokens is None:
            max_prompt_tokens = self.settings.max_prompt_tokens

        # Build messages to estimate
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        estimated_tokens = self._estimate_messages_tokens(messages)

        # Check if we're at or over the limit
        if estimated_tokens > max_prompt_tokens:
            logger.error(
                f"Prompt size validation failed: estimated {estimated_tokens} tokens "
                f"exceeds max {max_prompt_tokens} tokens"
            )
            raise PromptTooLargeError(estimated_tokens, max_prompt_tokens)

        # Warn if approaching limit (> 80%)
        warning_threshold = max_prompt_tokens * 0.8
        if estimated_tokens > warning_threshold:
            logger.warning(
                f"Prompt size approaching limit: estimated {estimated_tokens} tokens "
                f"({estimated_tokens / max_prompt_tokens * 100:.1f}% of {max_prompt_tokens} max)"
            )

        return estimated_tokens

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter.

        Args:
            attempt: The current retry attempt number (0-indexed)

        Returns:
            Sleep duration in seconds
        """
        # Exponential backoff: base * 2^attempt, capped at 8 seconds
        base_delay = self.settings.llm_retry_base_delay
        exponential = min(base_delay * (2 ** attempt), 8.0)
        # Add jitter: 0-1 seconds to prevent thundering herd
        jitter = random.uniform(0, 1)
        return exponential + jitter

    def _should_fallback(self, error: Exception) -> bool:
        """Check if an error should trigger fallback to secondary model (ML-QW-2).

        Fallback is appropriate for:
        - Model-specific errors (model overloaded, not available)
        - Persistent failures after retries
        - Non-transient API errors

        Args:
            error: The exception that was raised

        Returns:
            True if fallback should be attempted
        """
        if not self.fallback_enabled:
            return False

        # Check for model-specific errors that warrant fallback
        if isinstance(error, APIStatusError):
            # Model unavailable, service overloaded, or quota exceeded
            if error.status_code in {503, 529}:  # 529 = model overloaded on some APIs
                return True
            # Check error message for model-specific issues
            error_msg = str(error).lower()
            if any(phrase in error_msg for phrase in [
                "model", "overloaded", "capacity", "unavailable"
            ]):
                return True

        return False

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error should trigger a retry.

        Args:
            error: The exception that was raised

        Returns:
            True if the error is transient and should be retried
        """
        # Connection and timeout errors are retryable
        if isinstance(error, (TimeoutError, ConnectionError, APIConnectionError, APITimeoutError)):
            return True

        # API status errors with specific codes are retryable
        if isinstance(error, APIStatusError):
            return error.status_code in RETRYABLE_STATUS_CODES

        return False

    def _log_token_usage(self, usage, model: str, streaming: bool = False) -> None:
        """Log token usage for cost monitoring and debugging (ML-QW-1).

        Logs prompt tokens, completion tokens, and total tokens with the model name.
        Uses structured logging format for easy parsing by log aggregators.

        Args:
            usage: The usage object from the API response
            model: The model name/ID used for the request
            streaming: Whether this was a streaming request
        """
        if usage is None:
            logger.debug("Token usage not available in response")
            return

        prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
        completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
        total_tokens = getattr(usage, 'total_tokens', 0) or prompt_tokens + completion_tokens

        logger.info(
            "LLM token usage",
            extra={
                "token_usage": {
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "streaming": streaming,
                }
            }
        )


    async def _generate_with_model(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        max_retries: int,
    ) -> str:
        """Internal method to generate completion with a specific model (ML-QW-2).

        Args:
            model: The model to use for generation
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_retries: Maximum retry attempts

        Returns:
            The generated text with thinking tags stripped

        Raises:
            Exception: If max retries exceeded
        """
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=0.95,
                    max_tokens=max_tokens,
                    frequency_penalty=0,
                    presence_penalty=0,
                )

                # Log token usage for cost monitoring (ML-QW-1)
                self._log_token_usage(response.usage, model, streaming=False)

                content = response.choices[0].message.content or ""
                return strip_thinking_tags(content)

            except Exception as e:
                last_error = e

                # Don't retry non-retryable errors
                if not self._is_retryable_error(e):
                    logger.error(f"Non-retryable error on LLM call with {model}: {type(e).__name__}: {e}")
                    raise

                # Don't retry if we've exhausted attempts
                if attempt >= max_retries:
                    logger.error(
                        f"LLM call with {model} failed after {max_retries + 1} attempts. "
                        f"Last error: {type(e).__name__}: {e}"
                    )
                    raise

                # Calculate backoff and retry
                backoff = self._calculate_backoff(attempt)
                logger.warning(
                    f"Retryable error on attempt {attempt + 1}/{max_retries + 1} with {model}: "
                    f"{type(e).__name__}: {e}. Retrying in {backoff:.2f}s"
                )
                await asyncio.sleep(backoff)

        if last_error:
            raise last_error
        raise Exception("Unexpected error in LLM generate")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.6,
        max_tokens: int = 4096,
        max_retries: int | None = None,
        validate_size: bool = True,
        user_id: str | None = None,
    ) -> str:
        """Generate a completion (non-streaming) with retry logic and model fallback.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            max_retries: Maximum retry attempts (default: from settings)
            validate_size: Whether to validate prompt size before sending
            user_id: User ID for per-user rate limiting (SEC-009)

        Returns:
            The generated text with thinking tags stripped

        Raises:
            PromptTooLargeError: If prompt exceeds max_prompt_tokens (when validate_size=True)
            RateLimitExceededError: If rate limit exceeded after timeout
            Exception: If max retries exceeded on both primary and fallback models
        """
        if max_retries is None:
            max_retries = self.settings.llm_max_retries

        # Validate prompt size before making API call (ML-P1-3)
        if validate_size:
            self._validate_prompt_size(prompt, system_prompt)

        # Get per-user rate limiter (SEC-009)
        rate_limiter = await self._get_rate_limiter(user_id)

        if not await rate_limiter.wait_for_slot():
            remaining, retry_after = await rate_limiter.get_remaining()
            raise RateLimitExceededError(user_id or "anonymous", retry_after)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Try primary model first
        try:
            return await self._generate_with_model(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=max_retries,
            )
        except Exception as primary_error:
            # ML-QW-2: Check if we should fall back to secondary model
            if self._should_fallback(primary_error) and self.fallback_model:
                logger.warning(
                    f"Primary model {self.model} failed, falling back to {self.fallback_model}",
                    extra={
                        "primary_model": self.model,
                        "fallback_model": self.fallback_model,
                        "primary_error": str(primary_error),
                    }
                )
                try:
                    return await self._generate_with_model(
                        model=self.fallback_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        max_retries=max_retries,
                    )
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback model {self.fallback_model} also failed",
                        extra={
                            "primary_model": self.model,
                            "fallback_model": self.fallback_model,
                            "primary_error": str(primary_error),
                            "fallback_error": str(fallback_error),
                        }
                    )
                    # Re-raise the fallback error as it's more recent
                    raise fallback_error
            else:
                # No fallback available or not appropriate, re-raise original error
                raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.6,
        max_tokens: int = 4096,
        max_retries: int | None = None,
        validate_size: bool = True,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion with retry logic.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            max_retries: Maximum retry attempts (default: from settings)
            validate_size: Whether to validate prompt size before sending
            user_id: User ID for per-user rate limiting (SEC-009)

        Yields:
            Generated text chunks with thinking tags stripped

        Raises:
            PromptTooLargeError: If prompt exceeds max_prompt_tokens (when validate_size=True)
            RateLimitExceededError: If rate limit exceeded after timeout
            Exception: If max retries exceeded
        """
        if max_retries is None:
            max_retries = self.settings.llm_max_retries

        # Validate prompt size before making API call (ML-P1-3)
        if validate_size:
            self._validate_prompt_size(prompt, system_prompt)

        # Get per-user rate limiter (SEC-009)
        rate_limiter = await self._get_rate_limiter(user_id)

        if not await rate_limiter.wait_for_slot():
            remaining, retry_after = await rate_limiter.get_remaining()
            raise RateLimitExceededError(user_id or "anonymous", retry_after)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=0.95,
                    max_tokens=max_tokens,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stream=True,
                    stream_options={"include_usage": True},  # Request usage in stream (ML-QW-1)
                )

                # Buffer for thinking tag stripping in streaming mode
                buffer = ""
                in_thinking_block = False
                stream_usage = None  # Track usage from final chunk (ML-QW-1)

                async for chunk in stream:
                    # Capture usage from the final chunk (ML-QW-1)
                    if hasattr(chunk, 'usage') and chunk.usage is not None:
                        stream_usage = chunk.usage
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        buffer += content

                        # Handle thinking tags in streaming
                        while True:
                            if not in_thinking_block:
                                # Look for start of thinking block
                                think_start = buffer.find("<think>")
                                if think_start != -1:
                                    # Yield content before the tag
                                    if think_start > 0:
                                        yield buffer[:think_start]
                                    buffer = buffer[think_start + 7:]  # Skip <think>
                                    in_thinking_block = True
                                else:
                                    # Check if we might be at the start of a tag
                                    if buffer.endswith("<") or buffer.endswith("<t") or \
                                       buffer.endswith("<th") or buffer.endswith("<thi") or \
                                       buffer.endswith("<thin") or buffer.endswith("<think"):
                                        # Keep partial tag in buffer
                                        break
                                    # Safe to yield everything
                                    if buffer:
                                        yield buffer
                                        buffer = ""
                                    break
                            else:
                                # Look for end of thinking block
                                think_end = buffer.find("</think>")
                                if think_end != -1:
                                    # Discard thinking content
                                    buffer = buffer[think_end + 8:]  # Skip </think>
                                    in_thinking_block = False
                                else:
                                    # Still inside thinking block, keep buffering
                                    break

                # Yield any remaining content (not in thinking block)
                if buffer and not in_thinking_block:
                    yield buffer

                # Log token usage for streaming response (ML-QW-1)
                self._log_token_usage(stream_usage, self.model, streaming=True)

                return  # Success, exit retry loop

            except Exception as e:
                last_error = e

                # Don't retry non-retryable errors
                if not self._is_retryable_error(e):
                    logger.error(f"Non-retryable error on streaming LLM call: {type(e).__name__}: {e}")
                    raise

                # Don't retry if we've exhausted attempts
                if attempt >= max_retries:
                    logger.error(
                        f"Streaming LLM call failed after {max_retries + 1} attempts. "
                        f"Last error: {type(e).__name__}: {e}"
                    )
                    raise

                # Calculate backoff and retry
                backoff = self._calculate_backoff(attempt)
                logger.warning(
                    f"Retryable error on streaming attempt {attempt + 1}/{max_retries + 1}: "
                    f"{type(e).__name__}: {e}. Retrying in {backoff:.2f}s"
                )
                await asyncio.sleep(backoff)

        # This should never be reached, but just in case
        if last_error:
            raise last_error

    async def close(self):
        """Close connections."""
        if self._redis:
            await self._redis.close()
        self._rate_limiters.clear()


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
