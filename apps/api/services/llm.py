"""LLM client for NVIDIA NIM API with rate limiting."""

import asyncio
import re
import time
from typing import AsyncIterator

from openai import AsyncOpenAI
import redis.asyncio as redis

from config import get_settings


def strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> tags from model output."""
    # Remove thinking blocks
    text = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
    return text.strip()


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis_client: redis.Redis, key: str, max_requests: int, window: int):
        self.redis = redis_client
        self.key = f"ratelimit:{key}"
        self.max_requests = max_requests
        self.window = window

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
            return False
        return True

    async def wait_for_slot(self, timeout: float = 30.0) -> bool:
        """Wait until a rate limit slot is available."""
        start = time.time()
        while time.time() - start < timeout:
            if await self.acquire():
                return True
            await asyncio.sleep(0.5)
        return False


class LLMClient:
    """Client for NVIDIA NIM Llama API with rate limiting."""

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self.settings.nvidia_api_key,
        )
        self.model = self.settings.nvidia_model
        self._redis: redis.Redis | None = None
        self._rate_limiter: RateLimiter | None = None

    async def _get_rate_limiter(self) -> RateLimiter:
        """Get or create rate limiter."""
        if self._rate_limiter is None:
            self._redis = redis.from_url(self.settings.redis_url)
            self._rate_limiter = RateLimiter(
                self._redis,
                "nvidia_api",
                self.settings.rate_limit_requests,
                self.settings.rate_limit_window,
            )
        return self._rate_limiter

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.6,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a completion (non-streaming)."""
        rate_limiter = await self._get_rate_limiter()

        if not await rate_limiter.wait_for_slot():
            raise Exception("Rate limit exceeded. Please try again later.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            frequency_penalty=0,
            presence_penalty=0,
        )

        content = response.choices[0].message.content or ""
        return strip_thinking_tags(content)

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.6,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Generate a streaming completion."""
        rate_limiter = await self._get_rate_limiter()

        if not await rate_limiter.wait_for_slot():
            raise Exception("Rate limit exceeded. Please try again later.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            frequency_penalty=0,
            presence_penalty=0,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    async def close(self):
        """Close connections."""
        if self._redis:
            await self._redis.close()


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
