"""
API Routes - All FastAPI endpoints for the Codebase Explainer.
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.core.vector_store import vector_store
from app.services.parser import code_parser
from app.services.llm import llm_service
from app.services.session import session_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request/Response Models ────────────────────────────────────────────

class GithubIngestRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        if not ("github.com" in v or "/" in v):
            raise ValueError("Must be a GitHub URL or user/repo format")
        return v


class ChatRequest(BaseModel):
    session_id: str
    question: str
    question_type: str = "general"  # general, explain, flow, issues, architecture
    filter_file: Optional[str] = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Question too short")
        if len(v) > 2000:
            raise ValueError("Question too long (max 2000 chars)")
        return v


class FileExplainRequest(BaseModel):
    session_id: str
    file_path: str


class SessionDeleteRequest(BaseModel):
    session_id: str


# ─── Ingest Endpoints ────────────────────────────────────────────────────

async def _index_codebase(session_id: str, files):
    """Background task: build chunks and index into vector store."""
    try:
        chunks = code_parser.build_chunks(files)
        count = vector_store.add_chunks(session_id, chunks)
        session = session_manager.get_session(session_id)
        if session:
            session.chunk_count = count
        logger.info(f"Indexed {count} chunks for session {session_id[:8]}...")
    except Exception as e:
        logger.error(f"Indexing failed for session {session_id[:8]}...: {e}")


@router.post("/ingest/zip")
async def ingest_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload and index a ZIP file of source code."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only .zip files are supported")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(413, f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    try:
        files, stats = code_parser.parse_zip(content)
    except Exception as e:
        raise HTTPException(422, f"Failed to parse ZIP: {str(e)}")

    if not files:
        raise HTTPException(422, "No supported code files found in ZIP")

    file_tree = code_parser.get_file_tree(files)
    session = session_manager.create_session(
        source="zip",
        source_name=file.filename,
        files=files,
        file_tree=file_tree,
        stats=stats,
    )

    # Index in background
    background_tasks.add_task(_index_codebase, session.session_id, files)

    return {
        "session_id": session.session_id,
        "message": f"Parsing complete. Indexing {len(files)} files in background...",
        "stats": stats,
        "file_tree": file_tree,
        "source_name": file.filename,
    }


@router.post("/ingest/github")
async def ingest_github(
    request: GithubIngestRequest,
    background_tasks: BackgroundTasks,
):
    """Clone and index a public GitHub repository."""
    try:
        files, stats = await code_parser.parse_github_repo(request.repo_url)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch GitHub repo: {str(e)}")

    if not files:
        raise HTTPException(422, "No supported code files found in repository")

    file_tree = code_parser.get_file_tree(files)
    session = session_manager.create_session(
        source="github",
        source_name=request.repo_url,
        files=files,
        file_tree=file_tree,
        stats=stats,
    )

    background_tasks.add_task(_index_codebase, session.session_id, files)

    return {
        "session_id": session.session_id,
        "message": f"Repository fetched. Indexing {len(files)} files in background...",
        "stats": stats,
        "file_tree": file_tree,
        "source_name": request.repo_url,
    }


# ─── Session Endpoints ───────────────────────────────────────────────────

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session info and indexing status."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found or expired")

    vs_stats = vector_store.get_collection_stats(session_id)

    return {
        **session.to_dict(),
        "indexing_complete": vs_stats["total_chunks"] > 0,
        "chunks_indexed": vs_stats["total_chunks"],
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its vector data."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session_manager.delete_session(session_id)
    vector_store.delete_session(session_id)

    return {"message": "Session deleted successfully"}


# ─── Chat / Query Endpoints ──────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest):
    """Ask a question about the codebase using RAG with streaming response."""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found or expired. Please re-upload your codebase.")

    async def generate():
        # Check cache
        cached = session_manager.query_cache.get(
            request.session_id, request.question, request.question_type
        )
        if cached:
            meta = {
                "type": "metadata",
                "sources": [],
                "cached": True,
                "question_type": request.question_type
            }
            yield f"data: {json.dumps(meta)}\n\n"
            yield f"data: {json.dumps({'type': 'chunk', 'text': cached})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Retrieve relevant chunks
        try:
            chunks = vector_store.query(
                session_id=request.session_id,
                query_text=request.question,
                filter_file=request.filter_file,
            )
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to retrieve context from codebase'})}\n\n"
            return

        # Format sources
        sources = [
            {
                "file_path": c["metadata"]["file_path"],
                "language": c["metadata"]["language"],
                "start_line": c["metadata"].get("start_line"),
                "end_line": c["metadata"].get("end_line"),
                "relevance": c.get("relevance_score", 0),
            }
            for c in chunks[:5]
        ]

        meta = {
            "type": "metadata",
            "sources": sources,
            "cached": False,
            "question_type": request.question_type
        }
        yield f"data: {json.dumps(meta)}\n\n"

        full_answer = []
        try:
            async for text_chunk in llm_service.stream_chat(
                question=request.question,
                context_chunks=chunks,
                chat_history=session.chat_history,
                question_type=request.question_type,
            ):
                full_answer.append(text_chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'text': text_chunk})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        final_answer = "".join(full_answer)

        # Cache response
        session_manager.query_cache.set(
            request.session_id, request.question, request.question_type, final_answer
        )

        # Update chat history
        session.add_message("user", request.question)
        session.add_message("assistant", final_answer)

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/explain/file")
async def explain_file(request: FileExplainRequest):
    """Get an AI explanation of a specific file."""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Find file in session
    target_file = next(
        (f for f in session.files if f.path == request.file_path), None
    )
    if not target_file:
        raise HTTPException(404, f"File '{request.file_path}' not found in session")

    # Check cache
    cache_key = f"file_explain:{request.file_path}"
    cached = session_manager.query_cache.get(
        request.session_id, cache_key, "explain"
    )
    if cached:
        return {"explanation": cached, "cached": True, "file_path": request.file_path}

    try:
        explanation = await llm_service.generate_file_summary(
            file_path=target_file.path,
            content=target_file.content,
            language=target_file.language,
        )
    except Exception as e:
        raise HTTPException(503, f"Failed to generate explanation: {str(e)}")

    session_manager.query_cache.set(
        request.session_id, cache_key, "explain", explanation
    )

    return {
        "explanation": explanation,
        "cached": False,
        "file_path": request.file_path,
        "language": target_file.language,
        "lines": target_file.lines,
    }


@router.get("/file/{session_id}")
async def get_file_content(session_id: str, path: str):
    """Get the raw content of a file in the session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    target_file = next((f for f in session.files if f.path == path), None)
    if not target_file:
        raise HTTPException(404, f"File '{path}' not found")

    return {
        "path": target_file.path,
        "content": target_file.content,
        "language": target_file.language,
        "lines": target_file.lines,
        "size_bytes": target_file.size_bytes,
    }


# ─── Utility Endpoints ───────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions():
    """List all active sessions (admin endpoint)."""
    return {
        "sessions": session_manager.list_sessions(),
        "total": session_manager.active_sessions,
        "cache_size": session_manager.query_cache.size,
    }


@router.get("/sample-prompts")
async def get_sample_prompts():
    """Return sample prompts for demo purposes."""
    return {
        "prompts": [
            {
                "category": "Architecture",
                "type": "architecture",
                "question": "What is the overall architecture of this codebase? Explain the main components and how they interact.",
            },
            {
                "category": "Execution Flow",
                "type": "flow",
                "question": "Trace the execution flow from the entry point. How does a request travel through this system?",
            },
            {
                "category": "Code Quality",
                "type": "issues",
                "question": "What are the main code quality issues, potential bugs, or security vulnerabilities in this codebase?",
            },
            {
                "category": "Dependencies",
                "type": "general",
                "question": "What are the main dependencies this project relies on and why?",
            },
            {
                "category": "Getting Started",
                "type": "general",
                "question": "How would a new developer set up and run this project locally?",
            },
            {
                "category": "Testing",
                "type": "general",
                "question": "What is the testing strategy? Are there unit tests, integration tests, or end-to-end tests?",
            },
            {
                "category": "API Design",
                "type": "explain",
                "question": "What APIs does this project expose? Describe the endpoints and their purpose.",
            },
            {
                "category": "Data Flow",
                "type": "flow",
                "question": "How does data flow through this application? Describe the data models and transformations.",
            },
        ]
    }
