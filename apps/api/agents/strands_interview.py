"""Agent-native interview agent backed by Strands Agents SDK.

Replaces the hand-rolled FSM in interview.py with a Strands Agent that
owns the interview flow via system prompt + tools. The LLM naturally
follows the interview structure; KG tools provide context-aware guidance.
"""

from typing import AsyncIterator

from strands import Agent

from agents.tools.kg_tools import check_prior_decisions, search_knowledge
from models.schemas import DecisionTrace, Entity
from services.llm_providers import get_strands_model
from utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a decision capture assistant helping engineers document their technical decisions.

Your job is to guide a natural conversation that captures these 5 components:

1. TRIGGER — What problem, need, or event prompted the decision
2. CONTEXT — Background, constraints, environment, team situation
3. OPTIONS — ALL alternatives considered, including rejected ones
4. DECISION — What was ultimately chosen
5. RATIONALE — Why this choice was made over the alternatives

## Interview Guidelines

- Ask ONE question at a time (never multiple questions in one response)
- Keep responses concise: 2-3 sentences max
- Be conversational, warm, and encouraging
- Reference something specific the user said to show you're listening
- Probe deeper when answers are vague (e.g. "it was best" → ask for specific trade-offs)
- Progress naturally through the components — don't rush, but don't linger unnecessarily
- When the user mentions a technology or approach, use check_prior_decisions to see \
if there's relevant history in their knowledge graph
- When all 5 components are well-covered, summarize what you captured and confirm with the user

## Anti-patterns to Avoid

- Asking multiple questions at once
- Being too formal or robotic
- Accepting vague rationale without probing
- Moving on before understanding the root cause
- Not asking about rejected alternatives
- Ending without confirming the captured information
"""


class StrandsInterviewAgent:
    """Interview agent backed by Strands Agent SDK.

    Same external interface as InterviewAgent for drop-in replacement.
    """

    def __init__(self, fast_mode: bool = False, user_id: str | None = None):
        self.fast_mode = fast_mode
        self.user_id = user_id

        if not fast_mode:
            model = get_strands_model()
            self._agent = Agent(
                model=model,
                tools=[check_prior_decisions, search_knowledge],
                system_prompt=SYSTEM_PROMPT,
                callback_handler=None,
                state={"user_id": user_id or "anonymous"},
            )
        else:
            self._agent = None

    def _set_history(self, history: list[dict]) -> None:
        """Load conversation history into the agent's message buffer."""
        if not self._agent:
            return
        messages = []
        for msg in history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}],
            })
        self._agent.messages = messages

    async def process_message(
        self,
        user_message: str,
        history: list[dict],
    ) -> tuple[str, list[Entity]]:
        """Process a user message and generate a response."""
        if self.fast_mode:
            return self._generate_fallback_response(user_message, history), []

        self._set_history(history)

        try:
            result = await self._agent.invoke_async(user_message)
            response_text = ""
            if result and result.message and result.message.get("content"):
                for block in result.message["content"]:
                    if "text" in block:
                        response_text += block["text"]
            return response_text or "Could you tell me more about that?", []

        except Exception as e:
            logger.error(f"Strands agent error: {e}")
            return self._generate_fallback_response(user_message, history), []

    async def stream_response(
        self,
        user_message: str,
        history: list[dict],
    ) -> AsyncIterator[tuple[str, list[Entity]]]:
        """Stream a response for WebSocket use."""
        if self.fast_mode:
            yield self._generate_fallback_response(user_message, history), []
            return

        self._set_history(history)

        try:
            async for event in self._agent.stream_async(user_message):
                if "data" in event:
                    chunk = event["data"]
                    if chunk:
                        yield chunk, []
        except Exception as e:
            logger.error(f"Strands agent streaming error: {e}")
            yield self._generate_fallback_response(user_message, history), []

    async def synthesize_decision(self, history: list[dict]) -> dict:
        """Synthesize a complete decision trace from the conversation."""
        if not self._agent:
            return self._create_default_decision(history)

        self._set_history(history)

        synthesis_prompt = (
            "Based on our conversation, synthesize a complete decision trace. "
            "Extract the trigger, context, options considered, final decision, "
            "rationale, and your confidence (0.0-1.0) in how complete this trace is."
        )

        try:
            result = await self._agent.invoke_async(
                synthesis_prompt,
                structured_output_model=DecisionTrace,
            )

            if result and result.structured_output:
                return result.structured_output.model_dump()

            logger.warning("Structured output was empty, using fallback")
            return self._create_default_decision(history)

        except Exception as e:
            logger.error(f"Decision synthesis failed: {e}")
            return self._create_default_decision(history)

    def _generate_fallback_response(self, user_message: str, history: list[dict]) -> str:
        """Generate a pre-written fallback response based on conversation progress."""
        user_responses = [m for m in history if m["role"] == "user" and len(m["content"]) > 20]
        count = len(user_responses)

        user_words = user_message.strip().split()
        topic_hint = " ".join(user_words[:6]) if user_words else ""
        topic_suffix = f' — "{topic_hint}"' if topic_hint else ""

        if count == 0:
            return (
                f"Thanks for sharing{topic_suffix}. "
                "To capture this properly: what was the underlying problem or need that "
                "prompted this decision? Was there a specific event, deadline, or pain point?"
            )
        elif count == 1:
            return (
                "That helps set the scene. "
                "What constraints were you working within at the time — "
                "team size, existing tech stack, timeline, or budget considerations?"
            )
        elif count == 2:
            return (
                "Understood. What alternatives did you actually evaluate? "
                "Even if you quickly ruled some out, it's valuable to capture them "
                "as rejected paths. What other approaches came up?"
            )
        elif count == 3:
            return (
                "Good. And what was the final decision — "
                "the specific choice you made from those options?"
            )
        elif count == 4:
            return (
                "Almost done. Why did you choose this over the alternatives? "
                "What were the 1-3 key reasons or trade-offs that tipped the balance?"
            )
        else:
            return (
                "I have everything I need. Saving this decision to your knowledge graph now. "
                "You can view it in the Timeline or Graph view, or capture another decision."
            )

    def _create_default_decision(self, history: list[dict]) -> dict:
        """Create a default decision structure from conversation history."""
        user_messages = [m["content"] for m in history if m["role"] == "user"]
        return {
            "trigger": user_messages[0] if len(user_messages) > 0 else "Unknown trigger",
            "context": user_messages[1] if len(user_messages) > 1 else "",
            "options": [],
            "decision": user_messages[3] if len(user_messages) > 3 else "",
            "rationale": user_messages[4] if len(user_messages) > 4 else "",
            "confidence": 0.3,
        }
