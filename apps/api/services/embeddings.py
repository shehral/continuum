"""Embedding service using NVIDIA NV-EmbedQA model for semantic search."""

import asyncio
from typing import List

from openai import AsyncOpenAI

from config import get_settings


class EmbeddingService:
    """Generate embeddings using NVIDIA's Llama-based embedding model."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.nvidia_embedding_api_key,
            base_url="https://integrate.api.nvidia.com/v1",
        )
        self.model = "nvidia/llama-3.2-nv-embedqa-1b-v2"
        self.dimensions = 2048  # Model output dimensions

    async def embed_text(self, text: str, input_type: str = "passage") -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed
            input_type: "query" for search queries, "passage" for documents

        Returns:
            List of floats representing the embedding vector
        """
        response = await self.client.embeddings.create(
            input=[text],
            model=self.model,
            encoding_format="float",
            extra_body={"input_type": input_type, "truncate": "END"}
        )
        return response.data[0].embedding

    async def embed_texts(
        self,
        texts: List[str],
        input_type: str = "passage",
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Args:
            texts: List of texts to embed
            input_type: "query" for search queries, "passage" for documents
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.client.embeddings.create(
                input=batch,
                model=self.model,
                encoding_format="float",
                extra_body={"input_type": input_type, "truncate": "END"}
            )
            all_embeddings.extend([d.embedding for d in response.data])

        return all_embeddings

    async def embed_decision(self, decision: dict) -> List[float]:
        """
        Generate embedding for a decision by combining its key fields.

        Creates a rich text representation that captures the full context.
        """
        # Combine all relevant fields into a semantic representation
        text_parts = [
            f"Decision Trigger: {decision.get('trigger', '')}",
            f"Context: {decision.get('context', '')}",
            f"Options Considered: {', '.join(decision.get('options', []))}",
            f"Final Decision: {decision.get('decision', '')}",
            f"Rationale: {decision.get('rationale', '')}",
        ]
        combined_text = "\n".join(text_parts)
        return await self.embed_text(combined_text, input_type="passage")

    async def embed_entity(self, entity: dict) -> List[float]:
        """
        Generate embedding for an entity.
        """
        text = f"{entity.get('type', 'concept')}: {entity.get('name', '')}"
        return await self.embed_text(text, input_type="passage")

    async def semantic_search(
        self,
        query: str,
        candidates: List[dict],
        top_k: int = 10
    ) -> List[dict]:
        """
        Perform semantic search over candidates.

        Args:
            query: Search query
            candidates: List of dicts with 'text' and 'embedding' fields
            top_k: Number of results to return

        Returns:
            Top-k most similar candidates with similarity scores
        """
        query_embedding = await self.embed_text(query, input_type="query")

        # Calculate cosine similarity
        scored = []
        for candidate in candidates:
            if 'embedding' in candidate:
                similarity = self._cosine_similarity(
                    query_embedding,
                    candidate['embedding']
                )
                scored.append({**candidate, 'similarity': similarity})

        # Sort by similarity descending
        scored.sort(key=lambda x: x['similarity'], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
