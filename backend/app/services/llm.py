"""
LLM Service - Groq API integration for fast inference.
Uses llama3-70b-8192 — free tier, 6000 tokens/min.
"""

import logging
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


SYSTEM_PROMPT = """You are an expert software engineer and code analyst.
You help developers understand codebases by providing clear, accurate, and insightful explanations.

Your responses should:
- Be technically precise and use proper programming terminology
- Reference specific file names, function names, and line numbers when relevant
- Explain the "why" behind code decisions, not just the "what"
- Identify potential issues, anti-patterns, and improvement opportunities
- Use markdown formatting for code blocks, lists, and headers
- Be concise but comprehensive

When analyzing code:
- Look for architectural patterns (MVC, microservices, event-driven, etc.)
- Identify dependencies and their relationships
- Note code quality indicators (error handling, testing, documentation)
- Highlight security concerns when relevant
"""


class GroqLLMService:
    """
    Wrapper around Groq's OpenAI-compatible API.
    Groq provides free-tier access to Llama3 with very fast inference.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_rag_prompt(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        question_type: str = "general",
    ) -> str:
        """Build a RAG-enhanced prompt with retrieved context."""

        if not context_chunks:
            return f"""No relevant code was found in the indexed codebase for this question.

Question: {question}

Please let the user know that you couldn't find relevant context and suggest they try rephrasing."""

        # Format context
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            meta = chunk["metadata"]
            relevance = chunk.get("relevance_score", 0)
            context_parts.append(
                f"--- Context {i} (relevance: {relevance:.2f}) ---\n"
                f"File: {meta['file_path']} | Language: {meta['language']} | "
                f"Lines: {meta.get('start_line', '?')}-{meta.get('end_line', '?')}\n\n"
                f"{chunk['text']}\n"
            )

        context = "\n".join(context_parts)

        type_instructions = {
            "general": "Answer the question based on the code context provided.",
            "explain": "Provide a thorough explanation of what this code does, its purpose, and how it works.",
            "flow": "Trace the execution flow step by step, explaining how data moves through the system.",
            "issues": "Identify bugs, code smells, security vulnerabilities, performance issues, and improvement opportunities.",
            "architecture": "Explain the architectural patterns, design decisions, and overall structure of this codebase.",
        }

        instruction = type_instructions.get(question_type, type_instructions["general"])

        return f"""Based on the following code context from the repository, {instruction}

<code_context>
{context}
</code_context>

Question: {question}

Provide a detailed, technically accurate response. Reference specific files and line numbers where relevant."""

    async def chat(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        question_type: str = "general",
    ) -> str:
        """Send a RAG-enhanced query to Groq and return the response."""

        if not self.api_key:
            return self._mock_response(question, context_chunks)

        rag_prompt = self._build_rag_prompt(question, context_chunks, question_type)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add chat history (last 4 turns for context window management)
        if chat_history:
            for turn in chat_history[-4:]:
                messages.append(turn)

        messages.append({"role": "user", "content": rag_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.MAX_TOKENS,
            "temperature": settings.TEMPERATURE,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    GROQ_API_URL,
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API error: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"LLM API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            raise RuntimeError(f"Failed to get LLM response: {str(e)}")

    async def stream_chat(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        question_type: str = "general",
    ) -> AsyncGenerator[str, None]:
        """Send a RAG-enhanced query to Groq and stream the response."""

        if not self.api_key:
            yield self._mock_response(question, context_chunks)
            return

        rag_prompt = self._build_rag_prompt(question, context_chunks, question_type)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add chat history (last 4 turns for context window management)
        if chat_history:
            for turn in chat_history[-4:]:
                messages.append(turn)

        messages.append({"role": "user", "content": rag_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": settings.MAX_TOKENS,
            "temperature": settings.TEMPERATURE,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    GROQ_API_URL,
                    headers=self.headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            content = data["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        except httpx.HTTPStatusError as e:
            # We must await e.response.aread() if we want the text in a stream block,
            # but usually it's raised before streaming starts if it's a 4xx.
            logger.error(f"Groq API error: {e.response.status_code}")
            raise RuntimeError(f"LLM API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM service stream error: {e}")
            raise RuntimeError(f"Failed to get LLM response: {str(e)}")

    def _mock_response(self, question: str, chunks: List[Dict]) -> str:
        """Fallback response when no API key is configured."""
        file_list = list(set(c["metadata"]["file_path"] for c in chunks[:3]))
        return (
            f"⚠️ **No GROQ_API_KEY configured.**\n\n"
            f"To enable AI responses, add your free Groq API key to `.env`.\n\n"
            f"**Your question:** {question}\n\n"
            f"**Relevant files found:** {', '.join(file_list) if file_list else 'None'}\n\n"
            f"Get a free Groq API key at: https://console.groq.com"
        )

    async def generate_file_summary(self, file_path: str, content: str, language: str) -> str:
        """Generate a concise summary of a single file."""
        if not self.api_key:
            return f"File: `{file_path}` ({language})\n\nAdd GROQ_API_KEY to enable AI summaries."

        prompt = f"""Analyze this {language} file and provide:
1. **Purpose**: What does this file do? (1-2 sentences)
2. **Key components**: Main classes, functions, or exports
3. **Dependencies**: What it imports/depends on
4. **Role in codebase**: How it fits in the larger system

File: {file_path}

```{language}
{content[:3000]}{'...[truncated]' if len(content) > 3000 else ''}
```"""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 600,
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


# Singleton
llm_service = GroqLLMService()
