"""
Vector Store - ChromaDB-based persistent vector storage.
Uses sentence-transformers for free local embeddings.
"""

import logging
import os
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB-backed vector store with local sentence-transformer embeddings.
    Zero cost — runs entirely locally.
    """

    def __init__(self):
        self._client: Optional[chromadb.Client] = None
        self._model = None
        self._collection = None
        self._session_id: Optional[str] = None

    def _get_client(self) -> chromadb.Client:
        if self._client is None:
            os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=settings.VECTOR_STORE_PATH,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info(f"ChromaDB initialized at {settings.VECTOR_STORE_PATH}")
        return self._client

    def _get_model(self):
        if self._model is None:
            logger.info("Loading lightweight ONNX embedding model to save memory...")
            self._model = DefaultEmbeddingFunction()
            logger.info("ONNX Embedding model loaded successfully")
        return self._model

    def _get_collection(self, session_id: str):
        client = self._get_client()
        collection_name = f"codebase_{session_id[:32]}"

        try:
            self._collection = client.get_collection(collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self._collection = client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Created new collection: {collection_name}")

        self._session_id = session_id
        return self._collection

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        model = self._get_model()
        return model(texts)

    def add_chunks(self, session_id: str, chunks: List[Dict[str, Any]]) -> int:
        """
        Add code chunks to the vector store.
        Each chunk: {id, text, metadata}
        """
        collection = self._get_collection(session_id)

        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        embeddings = self.embed_texts(texts)

        # Upsert in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            collection.upsert(
                ids=ids[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                documents=texts[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
            )

        logger.info(f"Indexed {len(chunks)} chunks for session {session_id[:8]}...")
        return len(chunks)

    def query(
        self,
        session_id: str,
        query_text: str,
        top_k: int = None,
        filter_file: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-k relevant chunks for a query.
        Optional: filter by specific file path.
        """
        top_k = top_k or settings.TOP_K_RESULTS
        collection = self._get_collection(session_id)

        query_embedding = self.embed_texts([query_text])[0]

        where = {"file_path": filter_file} if filter_file else None

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results["ids"] and results["ids"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                chunks.append({
                    "text": doc,
                    "metadata": meta,
                    "relevance_score": round(1 - dist, 4),
                })

        return chunks

    def get_collection_stats(self, session_id: str) -> Dict[str, Any]:
        """Return stats about the indexed codebase."""
        try:
            collection = self._get_collection(session_id)
            count = collection.count()
            return {"total_chunks": count, "session_id": session_id}
        except Exception:
            return {"total_chunks": 0, "session_id": session_id}

    def delete_session(self, session_id: str):
        """Delete all data for a session."""
        client = self._get_client()
        collection_name = f"codebase_{session_id[:32]}"
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception:
            pass

    def clear(self):
        """Reset in-memory state (not persistent data)."""
        self._collection = None
        self._session_id = None


# Singleton instance
vector_store = VectorStore()
