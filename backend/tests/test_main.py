"""
Tests for the AI Codebase Explainer backend.
Run with: pytest tests/ -v
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.parser import (
    code_parser, smart_chunk_code, detect_language,
    should_ignore, CodeFile
)

client = TestClient(app)


# ─── Health Check ─────────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


# ─── Language Detection ───────────────────────────────────────────────────

def test_detect_language_python():
    assert detect_language("main.py") == "python"

def test_detect_language_typescript():
    assert detect_language("index.tsx") == "typescript"

def test_detect_language_go():
    assert detect_language("server.go") == "go"

def test_detect_language_dockerfile():
    assert detect_language("Dockerfile") == "dockerfile"

def test_detect_language_unknown():
    result = detect_language("file.xyz")
    assert result == "text"


# ─── Ignore Rules ─────────────────────────────────────────────────────────

def test_ignore_node_modules():
    assert should_ignore("project/node_modules/lodash/index.js") is True

def test_ignore_pycache():
    assert should_ignore("app/__pycache__/main.cpython-311.pyc") is True

def test_ignore_binary():
    assert should_ignore("build/app.exe") is True

def test_allow_python():
    assert should_ignore("app/main.py") is False

def test_allow_typescript():
    assert should_ignore("src/index.tsx") is False


# ─── Chunking ─────────────────────────────────────────────────────────────

def test_small_file_single_chunk():
    content = "def hello():\n    print('hello')\n"
    chunks = smart_chunk_code(content, "test.py", "python")
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["chunk_type"] == "full_file"

def test_large_file_multiple_chunks():
    # Generate a large python file
    lines = ["def func_{}():".format(i) + "\n    pass\n" for i in range(100)]
    content = "\n".join(lines)
    chunks = smart_chunk_code(content, "large.py", "python", chunk_size=200)
    assert len(chunks) > 1

def test_chunk_has_required_fields():
    content = "x = 1\n" * 30
    chunks = smart_chunk_code(content, "test.py", "python")
    for chunk in chunks:
        assert "id" in chunk
        assert "text" in chunk
        assert "metadata" in chunk
        assert "file_path" in chunk["metadata"]
        assert "language" in chunk["metadata"]
        assert "chunk_index" in chunk["metadata"]

def test_chunk_ids_are_unique():
    content = "\n".join([f"def func_{i}():\n    return {i}" for i in range(50)])
    chunks = smart_chunk_code(content, "test.py", "python", chunk_size=100)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))


# ─── ZIP Parser ───────────────────────────────────────────────────────────

def make_zip(files: dict) -> bytes:
    """Helper to create in-memory ZIP bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return buf.getvalue()

def test_parse_zip_basic():
    zip_bytes = make_zip({
        "project/main.py": "print('hello')",
        "project/utils.js": "const x = 1;",
    })
    files, stats = code_parser.parse_zip(zip_bytes)
    assert len(files) == 2
    assert stats["parsed_files"] == 2

def test_parse_zip_ignores_node_modules():
    zip_bytes = make_zip({
        "project/main.py": "print('hello')",
        "project/node_modules/pkg/index.js": "module.exports = {}",
    })
    files, stats = code_parser.parse_zip(zip_bytes)
    file_paths = [f.path for f in files]
    assert not any("node_modules" in p for p in file_paths)

def test_parse_zip_empty():
    zip_bytes = make_zip({
        "project/image.png": b"\x89PNG\r\n",
    })
    files, stats = code_parser.parse_zip(zip_bytes)
    assert len(files) == 0

def test_parse_zip_stats():
    zip_bytes = make_zip({
        "project/main.py": "x = 1\ny = 2\n",
        "project/utils.py": "z = 3\n",
    })
    files, stats = code_parser.parse_zip(zip_bytes)
    assert stats["total_files"] >= 2
    assert stats["parsed_files"] == 2
    assert stats["total_lines"] >= 3


# ─── File Tree ────────────────────────────────────────────────────────────

def test_file_tree_structure():
    files = [
        CodeFile("src/main.py", "x=1", "python", 3, 1),
        CodeFile("src/utils/helper.py", "y=2", "python", 3, 1),
        CodeFile("README.md", "# Hello", "markdown", 6, 1),
    ]
    tree = code_parser.get_file_tree(files)
    types = {item["type"] for item in tree}
    assert "file" in types
    assert "directory" in types


# ─── API Endpoints ────────────────────────────────────────────────────────

def test_ingest_zip_endpoint():
    zip_bytes = make_zip({
        "myproject/main.py": "print('hello world')\n",
        "myproject/utils.py": "def add(a, b):\n    return a + b\n",
    })
    response = client.post(
        "/api/v1/ingest/zip",
        files={"file": ("myproject.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["stats"]["parsed_files"] == 2
    return data["session_id"]

def test_ingest_zip_wrong_format():
    response = client.post(
        "/api/v1/ingest/zip",
        files={"file": ("test.txt", b"not a zip", "text/plain")},
    )
    assert response.status_code == 400

def test_session_not_found():
    response = client.get("/api/v1/session/nonexistent-id")
    assert response.status_code == 404

def test_sample_prompts():
    response = client.get("/api/v1/sample-prompts")
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert len(data["prompts"]) > 0
    for p in data["prompts"]:
        assert "category" in p
        assert "question" in p
        assert "type" in p

def test_full_workflow():
    """Integration test: ingest → session check → chat."""
    # 1. Ingest
    zip_bytes = make_zip({
        "app/main.py": (
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "@app.get('/')\n"
            "def root():\n"
            "    return {'hello': 'world'}\n"
        ),
    })
    ingest_response = client.post(
        "/api/v1/ingest/zip",
        files={"file": ("app.zip", zip_bytes, "application/zip")},
    )
    assert ingest_response.status_code == 200
    session_id = ingest_response.json()["session_id"]

    # 2. Check session
    session_response = client.get(f"/api/v1/session/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["session_id"] == session_id

    # 3. File content
    file_response = client.get(
        f"/api/v1/file/{session_id}?path=main.py"
    )
    assert file_response.status_code == 200
    assert "fastapi" in file_response.json()["content"].lower()
