from typing import AsyncIterator
from enum import Enum
import json

from config import get_settings
from models.schemas import Entity
from services.extractor import DecisionExtractor
from services.llm import get_llm_client


class InterviewState(str, Enum):
    OPENING = "opening"
    TRIGGER = "trigger"
    CONTEXT = "context"
    OPTIONS = "options"
    DECISION = "decision"
    RATIONALE = "rationale"
    SUMMARIZING = "summarizing"


class InterviewAgent:
    """AI-powered interview agent for knowledge capture using NVIDIA Llama."""

    def __init__(self, fast_mode: bool = False):
        """Initialize the interview agent.

        Args:
            fast_mode: If True, uses pre-written responses for faster interaction.
                      If False, uses LLM for each response (slower but more dynamic).
        """
        self.llm = get_llm_client()
        self.extractor = DecisionExtractor()
        self.state = InterviewState.OPENING
        self.fast_mode = fast_mode

    def _get_system_prompt(self) -> str:
        return """You are a knowledge capture assistant helping engineers document their decisions.
Your goal is to extract a complete decision trace with:
1. Trigger - What prompted the decision
2. Context - Background information
3. Options - Alternatives considered
4. Decision - What was chosen
5. Rationale - Why it was chosen

Guide the conversation naturally. Ask follow-up questions to get complete information.
Be conversational but focused. When you have enough information for a stage, move to the next.

Current conversation state will be provided. Respond appropriately for that state."""

    def _get_stage_prompt(self, state: InterviewState) -> str:
        prompts = {
            InterviewState.OPENING: "Welcome the user and ask what decision or knowledge they want to capture.",
            InterviewState.TRIGGER: "Ask about what triggered this decision. What problem were they solving?",
            InterviewState.CONTEXT: "Ask about the context. What was the situation? What constraints existed?",
            InterviewState.OPTIONS: "Ask what alternatives were considered. What other approaches were possible?",
            InterviewState.DECISION: "Ask what was ultimately decided. What did they choose?",
            InterviewState.RATIONALE: "Ask why this decision was made. What factors influenced the choice?",
            InterviewState.SUMMARIZING: "Summarize the decision trace and confirm with the user.",
        }
        return prompts.get(state, "Continue the conversation naturally.")

    def _determine_next_state(self, history: list[dict]) -> InterviewState:
        """Determine the next state based on conversation history."""
        # Count substantial user responses
        user_responses = [
            m for m in history
            if m["role"] == "user" and len(m["content"]) > 20
        ]

        if len(user_responses) == 0:
            return InterviewState.TRIGGER
        elif len(user_responses) == 1:
            return InterviewState.CONTEXT
        elif len(user_responses) == 2:
            return InterviewState.OPTIONS
        elif len(user_responses) == 3:
            return InterviewState.DECISION
        elif len(user_responses) == 4:
            return InterviewState.RATIONALE
        else:
            return InterviewState.SUMMARIZING

    async def process_message(
        self,
        user_message: str,
        history: list[dict],
    ) -> tuple[str, list[Entity]]:
        """Process a user message and generate a response."""
        # Determine current state
        self.state = self._determine_next_state(history)

        # Fast mode: use pre-written responses for instant feedback
        if self.fast_mode:
            return self._generate_fallback_response(user_message, history), []

        # Build prompt
        system_prompt = self._get_system_prompt()
        stage_prompt = self._get_stage_prompt(self.state)

        # Format conversation history
        history_text = "\n".join(
            f"{m['role'].title()}: {m['content']}" for m in history[-10:]
        )

        prompt = f"""Current stage: {self.state.value}
Stage guidance: {stage_prompt}

Conversation so far:
{history_text}

User: {user_message}

Respond naturally as the interview assistant. Keep responses concise (2-3 sentences).
Ask follow-up questions when needed to get complete information."""

        try:
            response_text = await self.llm.generate(
                prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )

            # Skip entity extraction during chat for faster responses
            # Entities will be extracted when the session is completed
            return response_text, []

        except Exception as e:
            print(f"Error generating response: {e}")
            return self._generate_fallback_response(user_message, history), []

    def _generate_fallback_response(
        self,
        user_message: str,
        history: list[dict],
    ) -> str:
        """Generate a pre-written response for fast interaction."""
        self.state = self._determine_next_state(history)

        responses = {
            InterviewState.TRIGGER: "Great, that's a good start! Can you tell me more about the context? What was the situation you were in, and what constraints or requirements did you have?",
            InterviewState.CONTEXT: "I understand the situation better now. What alternatives or options did you consider before making this decision?",
            InterviewState.OPTIONS: "Those are interesting alternatives. What did you ultimately decide to do? What was your final choice?",
            InterviewState.DECISION: "Got it. Why did you choose this approach over the other options? What factors influenced your decision?",
            InterviewState.RATIONALE: "Excellent! I have all the key information now. Let me save this decision trace to your knowledge graph.",
            InterviewState.SUMMARIZING: "This decision has been captured! You can view it in the Knowledge Graph or start documenting another decision.",
        }

        return responses.get(
            self.state,
            "Thanks for sharing! What decision would you like to document? Tell me what triggered this decision or what problem you were trying to solve.",
        )

    async def stream_response(
        self,
        user_message: str,
        history: list[dict],
    ) -> AsyncIterator[tuple[str, list[Entity]]]:
        """Stream a response (for WebSocket use)."""
        # Determine current state
        self.state = self._determine_next_state(history)

        # Fast mode: return pre-written response immediately
        if self.fast_mode:
            response = self._generate_fallback_response(user_message, history)
            yield response, []
            return

        # Build prompt
        system_prompt = self._get_system_prompt()
        stage_prompt = self._get_stage_prompt(self.state)

        # Format conversation history
        history_text = "\n".join(
            f"{m['role'].title()}: {m['content']}" for m in history[-10:]
        )

        prompt = f"""Current stage: {self.state.value}
Stage guidance: {stage_prompt}

Conversation so far:
{history_text}

User: {user_message}

Respond naturally as the interview assistant. Keep responses concise (2-3 sentences).
Ask follow-up questions when needed to get complete information."""

        try:
            full_response = ""
            async for chunk in self.llm.generate_stream(
                prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            ):
                full_response += chunk
                yield chunk, []

            # Skip entity extraction for faster responses
            yield "", []

        except Exception as e:
            print(f"Error streaming response: {e}")
            yield self._generate_fallback_response(user_message, history), []

    async def synthesize_decision(self, history: list[dict]) -> dict:
        """Synthesize a complete decision trace from the conversation."""
        conversation_text = "\n".join(
            f"{m['role'].title()}: {m['content']}" for m in history
        )

        prompt = f"""Based on this interview conversation, synthesize a complete decision trace.

Conversation:
{conversation_text}

Return a JSON object with:
{{
  "trigger": "What prompted the decision",
  "context": "Background and constraints",
  "options": ["Option 1", "Option 2", ...],
  "decision": "What was decided",
  "rationale": "Why this was chosen",
  "confidence": 0.0-1.0 (how complete is this trace)
}}

Return ONLY valid JSON."""

        try:
            response = await self.llm.generate(prompt, temperature=0.3)
            text = response.strip()

            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            return json.loads(text)

        except Exception as e:
            print(f"Error synthesizing decision: {e}")
            return {}
