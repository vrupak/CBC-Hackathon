"""
Claude API Client for Q&A
Handles interactions with Claude for context-aware question answering
Adapted from ConceptMapperMVP for async/FastAPI usage
"""

import anthropic
from typing import List, Dict, Optional, Tuple, Any, AsyncGenerator
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude client"""
        self.api_key = api_key or ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def answer_question(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
    ) -> Tuple[str, bool]:
        """
        Get answer from Claude, optionally using provided context

        Args:
            question: User's question
            context: Optional context from Supermemory
            chat_history: Previous messages for context

        Returns:
            Tuple of (answer: str, context_used: bool)
        """
        try:
            # Build system prompt based on context availability
            if context:
                system_prompt = f"""You are an intelligent study assistant.
A user has uploaded study materials and is asking questions about them.

Here is the relevant study material from their documents:
<study_material>
{context}
</study_material>

IMPORTANT INSTRUCTIONS:
1. First, check if the study material contains relevant information for the user's question.
2. If YES: Prioritize using the study material to answer the question. You may supplement with additional knowledge if needed.
3. If NO: Acknowledge that the material doesn't cover this topic, then provide information from your general knowledge.
4. Always be clear about whether you're using the uploaded material or general knowledge.
5. Be concise, educational, and adapt explanations to the user's understanding level."""
                context_used = True
            else:
                system_prompt = """You are an AI Study Buddy, a helpful educational assistant.
You help students understand concepts, answer questions about their study materials, and provide explanations in a clear and engaging way.
Be supportive, patient, and adapt your explanations to the user's understanding level.
When answering, provide accurate, concise, and educational responses."""
                context_used = False

            # Build messages
            messages = []

            # Add chat history if available (last 5 messages for context)
            if chat_history:
                for msg in chat_history[-5:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

            # Add current question
            messages.append({"role": "user", "content": question})

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            )

            answer = response.content[0].text
            return answer, context_used

        except anthropic.APIError as e:
            print(f"[ERROR] Claude API error: {e}")
            return (
                "I encountered an issue processing your question. Please try again.",
                False,
            )
        except Exception as e:
            print(f"[ERROR] Unexpected error in answer_question: {e}")
            return (
                "I encountered an issue processing your question. Please try again.",
                False,
            )

    def extract_relevance_score(self, question: str, context: str) -> float:
        """
        Score how relevant context is to a question (0.0 to 1.0)

        Args:
            question: User's question
            context: Context text

        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": f"""Rate the relevance of this context to the question on a scale of 0 to 1.
Only output a single number between 0 and 1.

Question: {question}

Context: {context}""",
                }
            ]

            response = self.client.messages.create(
                model=self.model, max_tokens=10, messages=messages
            )

            score_text = response.content[0].text.strip()
            try:
                score = float(score_text)
                return min(1.0, max(0.0, score))
            except ValueError:
                return 0.5

        except Exception as e:
            print(f"[WARN] Error extracting relevance score: {e}")
            return 0.5

    def should_search_web(self, question: str, context: str) -> bool:
        """
        Determine if web search is needed based on context quality

        Args:
            question: User's question
            context: Retrieved context

        Returns:
            Boolean indicating if web search is needed
        """
        if not context or len(context.strip()) < 50:
            return True

        relevance_score = self.extract_relevance_score(question, context)
        return relevance_score < 0.5

    async def answer_with_web_search(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
        web_search_fn: Optional[callable] = None,
    ) -> Tuple[str, bool, bool]:
        """
        Answer question with web search fallback if context insufficient

        Workflow:
        1. If context is relevant → Use context
        2. If context is irrelevant → Search web
        3. Return answer with clear attribution

        Args:
            question: User's question
            context: Optional context from Supermemory
            chat_history: Conversation history
            web_search_fn: Async function to search web (receives query, returns results)

        Returns:
            Tuple of (answer, context_used, web_search_used)
        """
        web_search_used = False
        context_used = False
        final_context = context

        # Check if we should use context or search web
        if context and len(context.strip()) > 50:
            relevance = self.extract_relevance_score(question, context)
            if relevance >= 0.5:
                context_used = True
            else:
                # Context exists but not relevant - search web
                print(f"[INFO] Context relevance score: {relevance} (< 0.5, searching web)")
                if web_search_fn:
                    try:
                        web_results = await web_search_fn(question)
                        if web_results:
                            final_context = web_results
                            web_search_used = True
                            print(f"[INFO] Web search found {len(web_results)} results")
                    except Exception as e:
                        print(f"[WARN] Web search failed: {e}")
        elif not context or len(context.strip()) < 50:
            # No context - search web
            print(f"[INFO] No context from Supermemory, searching web")
            if web_search_fn:
                try:
                    web_results = await web_search_fn(question)
                    if web_results:
                        final_context = web_results
                        web_search_used = True
                        print(f"[INFO] Web search found {len(web_results)} results")
                except Exception as e:
                    print(f"[WARN] Web search failed: {e}")

        # Build system prompt with proper attribution
        if context_used:
            system_prompt = f"""You are an intelligent study assistant.
A user has uploaded study materials and is asking questions about them.

Here is the relevant study material from their documents:
<study_material>
{final_context}
</study_material>

IMPORTANT INSTRUCTIONS:
1. First, check if the study material contains relevant information for the user's question.
2. If YES: Prioritize using the study material to answer the question. You may supplement with additional knowledge if needed.
3. If NO: Acknowledge that the material doesn't cover this topic, then provide information from your general knowledge.
4. Always be clear about whether you're using the uploaded material or general knowledge.
5. Be concise, educational, and adapt explanations to the user's understanding level."""
        elif web_search_used:
            system_prompt = f"""You are an intelligent study assistant.
The user asked about a topic NOT covered in their uploaded study materials.
You have searched the web and found relevant information below.

IMPORTANT:
- First acknowledge that this information was NOT in the uploaded material
- Then explain the answer based on web search results
- Be clear that this is from web sources, not the uploaded material

Web search results:
<web_results>
{final_context}
</web_results>

Provide a clear, educational response that acknowledges the material gap."""
        else:
            system_prompt = """You are an AI Study Buddy, a helpful educational assistant.
You help students understand concepts, answer questions about their study materials, and provide explanations in a clear and engaging way.
Be supportive, patient, and adapt your explanations to the user's understanding level.
When answering, provide accurate, concise, and educational responses."""

        # Build messages
        messages = []
        if chat_history:
            for msg in chat_history[-5:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": question})

        # Get response from Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            )
            answer = response.content[0].text
            return answer, context_used, web_search_used
        except Exception as e:
            print(f"[ERROR] Claude API error: {e}")
            return (
                "I encountered an issue processing your question. Please try again.",
                False,
                False,
            )

    async def answer_with_web_search_stream(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
        web_search_fn: Optional[callable] = None,
    ):
        """
        Stream answer from Claude with web search fallback if context insufficient.
        Yields JSON strings with token-by-token chunks (async generator).

        Workflow:
        1. Check context relevance
        2. Skip web search for now (async calls not supported in sync generator)
        3. Stream response with metadata headers

        Args:
            question: User's question
            context: Optional context from Supermemory
            chat_history: Conversation history
            web_search_fn: Not used in streaming version

        Yields:
            JSON strings containing:
            - "metadata": Context/web flags (only first chunk)
            - "text": Text token or completion marker
        """
        context_used = False
        web_search_used = False
        final_context = context

        # Check if we should use context
        if context and len(context.strip()) > 50:
            relevance = self.extract_relevance_score(question, context)
            if relevance >= 0.5:
                context_used = True
            else:
                print(f"[INFO] Context relevance score: {relevance} (< 0.5)")
        elif not context or len(context.strip()) < 50:
            print(f"[INFO] No context from Supermemory")

        # Build system prompt with proper attribution
        if context_used:
            system_prompt = f"""You are an intelligent study assistant.
A user has uploaded study materials and is asking questions about them.

Here is the relevant study material from their documents:
<study_material>
{final_context}
</study_material>

IMPORTANT INSTRUCTIONS:
1. First, check if the study material contains relevant information for the user's question.
2. If YES: Prioritize using the study material to answer the question. You may supplement with additional knowledge if needed.
3. If NO: Acknowledge that the material doesn't cover this topic, then provide information from your general knowledge.
4. Always be clear about whether you're using the uploaded material or general knowledge.
5. Be concise, educational, and adapt explanations to the user's understanding level."""
        elif web_search_used:
            system_prompt = f"""You are an intelligent study assistant.
The user asked about a topic NOT covered in their uploaded study materials.
You have searched the web and found relevant information below.

IMPORTANT:
- First acknowledge that this information was NOT in the uploaded material
- Then explain the answer based on web search results
- Be clear that this is from web sources, not the uploaded material

Web search results:
<web_results>
{final_context}
</web_results>

Provide a clear, educational response that acknowledges the material gap."""
        else:
            system_prompt = """You are an AI Study Buddy, a helpful educational assistant.
You help students understand concepts, answer questions about their study materials, and provide explanations in a clear and engaging way.
Be supportive, patient, and adapt your explanations to the user's understanding level.
When answering, provide accurate, concise, and educational responses."""

        # Build messages
        messages = []
        if chat_history:
            for msg in chat_history[-5:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": question})

        # Stream response from Claude
        try:
            import json

            # Yield metadata on first chunk
            metadata = {
                "metadata": {
                    "context_used": context_used,
                    "web_search_used": web_search_used
                }
            }
            print(f"[CLAUDE] Yielding metadata: {metadata}")
            yield json.dumps(metadata) + "\n"

            # Stream the actual response
            print(f"[CLAUDE] Starting stream with model {self.model}")
            chunk_count = 0
            with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    chunk_count += 1
                    if chunk_count % 5 == 0:  # Log every 5th chunk to reduce verbosity
                        print(f"[CLAUDE] Chunk {chunk_count}: {text[:50]}...")
                    chunk = {
                        "text": text
                    }
                    yield json.dumps(chunk) + "\n"

                # Send completion signal
                print(f"[CLAUDE] Stream complete. Total chunks: {chunk_count}")
                yield json.dumps({"done": True}) + "\n"

        except Exception as e:
            print(f"[ERROR] Claude streaming error: {e}")
            error_chunk = {
                "error": str(e),
                "text": "I encountered an issue processing your question. Please try again."
            }
            yield json.dumps(error_chunk) + "\n"
