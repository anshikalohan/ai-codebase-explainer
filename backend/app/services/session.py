"""
Session Service - Manages user sessions and LRU caching.
Keeps parsed codebases in memory for fast repeated queries.
"""

import time
import hashlib
import logging
from collections import OrderedDict
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.parser import CodeFile

logger = logging.getLogger(__name__)


@dataclass
class Session:
    session_id: str
    source: str  # "zip" or "github"
    source_name: str
    files: List[CodeFile]
    file_tree: List[Dict[str, Any]]
    stats: Dict[str, Any]
    chunk_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    chat_history: List[Dict[str, str]] = field(default_factory=list)

    def touch(self):
        self.last_accessed = time.time()

    def add_message(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})
        # Keep last 20 turns
        if len(self.chat_history) > 40:
            self.chat_history = self.chat_history[-40:]

    @property
    def age_minutes(self) -> float:
        return (time.time() - self.created_at) / 60

    @property
    def idle_minutes(self) -> float:
        return (time.time() - self.last_accessed) / 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source": self.source,
            "source_name": self.source_name,
            "stats": {
                **self.stats,
                "chunk_count": self.chunk_count,
                "file_count": len(self.files),
            },
            "file_tree": self.file_tree,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "chat_turns": len(self.chat_history) // 2,
        }


class QueryCache:
    """
    Simple LRU cache for RAG query results.
    Key: (session_id, query_hash) -> response
    """

    def __init__(self, max_size: int = None, ttl: int = None):
        self.max_size = max_size or settings.MAX_CACHE_SIZE
        self.ttl = ttl or settings.CACHE_TTL_SECONDS
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def _make_key(self, session_id: str, query: str, query_type: str) -> str:
        raw = f"{session_id}:{query.lower().strip()}:{query_type}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, session_id: str, query: str, query_type: str) -> Optional[str]:
        key = self._make_key(session_id, query, query_type)
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() - entry["timestamp"] > self.ttl:
            del self._cache[key]
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)
        logger.debug(f"Cache hit for query: {query[:50]}...")
        return entry["response"]

    def set(self, session_id: str, query: str, query_type: str, response: str):
        key = self._make_key(session_id, query, query_type)

        if len(self._cache) >= self.max_size:
            # Remove oldest
            self._cache.popitem(last=False)

        self._cache[key] = {
            "response": response,
            "timestamp": time.time(),
        }
        self._cache.move_to_end(key)

    def invalidate_session(self, session_id: str):
        """Remove all cache entries for a session."""
        # We don't store session_id in key value, so just clear all on session delete
        # In production: store session_id separately
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class SessionManager:
    """
    In-memory session store with TTL and LRU eviction.
    For production, replace with Redis.
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._max_sessions = 50
        self.query_cache = QueryCache()

    def create_session(
        self,
        source: str,
        source_name: str,
        files: List[CodeFile],
        file_tree: List[Dict],
        stats: Dict[str, Any],
    ) -> Session:
        session_id = hashlib.sha256(
            f"{source_name}:{time.time()}".encode()
        ).hexdigest()[:32]

        session = Session(
            session_id=session_id,
            source=source,
            source_name=source_name,
            files=files,
            file_tree=file_tree,
            stats=stats,
        )

        # Evict old sessions if at capacity
        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()

        self._sessions[session_id] = session
        logger.info(f"Created session {session_id[:8]}... for {source_name}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session:
            session.touch()
        return session

    def delete_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
            self.query_cache.invalidate_session(session_id)
            logger.info(f"Deleted session {session_id[:8]}...")

    def _evict_oldest(self):
        """Remove the session with the oldest last_accessed time."""
        if not self._sessions:
            return
        oldest_id = min(self._sessions, key=lambda k: self._sessions[k].last_accessed)
        self.delete_session(oldest_id)
        logger.info(f"Evicted old session {oldest_id[:8]}...")

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    @property
    def active_sessions(self) -> int:
        return len(self._sessions)


# Singleton
session_manager = SessionManager()
