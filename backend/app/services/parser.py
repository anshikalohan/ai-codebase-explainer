"""
Code Parser Service - Extracts, filters, and chunks code files.
Handles ZIP uploads and GitHub repos with smart chunking strategy.
"""

import io
import re
import zipfile
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CodeFile:
    path: str
    content: str
    language: str
    size_bytes: int
    lines: int


@dataclass
class CodeChunk:
    id: str
    text: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    chunk_type: str  # "full_file", "class", "function", "block"
    chunk_index: int


def detect_language(file_path: str) -> str:
    """Map file extension to language name."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript", ".java": "java",
        ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
        ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".scala": "scala", ".r": "r", ".sh": "bash", ".bash": "bash",
        ".sql": "sql", ".html": "html", ".css": "css",
        ".scss": "scss", ".sass": "sass", ".vue": "vue",
        ".md": "markdown", ".json": "json", ".yaml": "yaml",
        ".yml": "yaml", ".toml": "toml", ".xml": "xml",
        ".tf": "terraform", ".dockerfile": "dockerfile",
    }
    ext = Path(file_path).suffix.lower()
    if "dockerfile" in file_path.lower():
        return "dockerfile"
    return ext_map.get(ext, "text")


def should_ignore(path: str) -> bool:
    """Check if a file/directory should be ignored."""
    parts = Path(path).parts
    for part in parts:
        if part in settings.IGNORED_DIRS:
            return True

    ext = Path(path).suffix.lower()
    if ext and ext not in settings.SUPPORTED_EXTENSIONS:
        # Allow extensionless files like Makefile, Dockerfile
        basename = Path(path).name
        if basename not in ["Makefile", "Dockerfile", "Gemfile", "Procfile"]:
            return True

    return False


def smart_chunk_code(
    content: str,
    file_path: str,
    language: str,
    chunk_size: int = None,
    overlap: int = None,
) -> List[Dict[str, Any]]:
    """
    Smart chunking strategy for code files:
    1. Prefer splitting at class/function boundaries
    2. Fall back to line-based chunking with overlap
    3. Small files: single chunk
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    lines = content.split("\n")
    total_lines = len(lines)

    # Small file: single chunk
    if total_lines <= 60 or len(content) <= chunk_size:
        chunk_id = hashlib.md5(f"{file_path}:0".encode()).hexdigest()[:16]
        return [{
            "id": chunk_id,
            "text": f"File: {file_path}\nLanguage: {language}\n\n{content}",
            "metadata": {
                "file_path": file_path,
                "language": language,
                "start_line": 1,
                "end_line": total_lines,
                "chunk_type": "full_file",
                "chunk_index": 0,
            }
        }]

    # Detect logical boundaries
    boundaries = _find_logical_boundaries(lines, language)

    chunks = []
    chunk_index = 0

    if boundaries and len(boundaries) > 1:
        # Split by logical boundaries
        for i, (start, end, chunk_type) in enumerate(boundaries):
            section_lines = lines[start:end]
            section_text = "\n".join(section_lines)

            # If section is too large, sub-chunk it
            if len(section_text) > chunk_size * 2:
                sub_chunks = _sliding_window_chunk(
                    section_lines, file_path, language,
                    chunk_size, overlap, chunk_index, start
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
            else:
                chunk_id = hashlib.md5(f"{file_path}:{chunk_index}".encode()).hexdigest()[:16]
                chunks.append({
                    "id": chunk_id,
                    "text": f"File: {file_path} [{chunk_type}]\nLanguage: {language}\n\n{section_text}",
                    "metadata": {
                        "file_path": file_path,
                        "language": language,
                        "start_line": start + 1,
                        "end_line": end,
                        "chunk_type": chunk_type,
                        "chunk_index": chunk_index,
                    }
                })
                chunk_index += 1
    else:
        # Sliding window fallback
        chunks = _sliding_window_chunk(
            lines, file_path, language, chunk_size, overlap, 0, 0
        )

    return chunks


def _find_logical_boundaries(
    lines: List[str], language: str
) -> List[Tuple[int, int, str]]:
    """Find class/function boundaries for smart splitting."""
    boundaries = []

    if language in ("python",):
        patterns = [
            (r"^class\s+\w+", "class"),
            (r"^def\s+\w+|^async\s+def\s+\w+", "function"),
        ]
    elif language in ("javascript", "typescript"):
        patterns = [
            (r"^(export\s+)?(default\s+)?(class|function)\s+\w+", "class/function"),
            (r"^(const|let|var)\s+\w+\s*=\s*(async\s+)?\(", "arrow_function"),
            (r"^(export\s+)?(const|function)\s+\w+", "export"),
        ]
    elif language in ("java", "kotlin", "csharp", "scala"):
        patterns = [
            (r"^\s*(public|private|protected|internal).*class\s+\w+", "class"),
            (r"^\s*(public|private|protected|internal|static).*\w+\s+\w+\s*\(", "method"),
        ]
    elif language == "go":
        patterns = [
            (r"^func\s+\w+", "function"),
            (r"^type\s+\w+\s+struct", "struct"),
        ]
    elif language == "rust":
        patterns = [
            (r"^(pub\s+)?fn\s+\w+", "function"),
            (r"^(pub\s+)?struct\s+\w+|^(pub\s+)?impl\s+\w+", "struct/impl"),
        ]
    else:
        return []

    section_starts = []
    for i, line in enumerate(lines):
        for pattern, label in patterns:
            if re.match(pattern, line):
                section_starts.append((i, label))
                break

    if not section_starts:
        return []

    for idx, (start, label) in enumerate(section_starts):
        end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
        boundaries.append((start, end, label))

    return boundaries


def _sliding_window_chunk(
    lines: List[str],
    file_path: str,
    language: str,
    chunk_size: int,
    overlap: int,
    start_index: int,
    line_offset: int,
) -> List[Dict[str, Any]]:
    """Sliding window chunking based on character count."""
    chunks = []
    chunk_index = start_index
    current_lines = []
    current_size = 0
    line_start = 0

    for i, line in enumerate(lines):
        current_lines.append(line)
        current_size += len(line) + 1

        if current_size >= chunk_size:
            text = "\n".join(current_lines)
            chunk_id = hashlib.md5(f"{file_path}:{chunk_index}".encode()).hexdigest()[:16]
            chunks.append({
                "id": chunk_id,
                "text": f"File: {file_path}\nLanguage: {language}\nLines: {line_offset+line_start+1}-{line_offset+i+1}\n\n{text}",
                "metadata": {
                    "file_path": file_path,
                    "language": language,
                    "start_line": line_offset + line_start + 1,
                    "end_line": line_offset + i + 1,
                    "chunk_type": "block",
                    "chunk_index": chunk_index,
                }
            })
            chunk_index += 1

            # Overlap: keep last N lines
            overlap_lines = current_lines[-max(1, overlap // 60):]
            current_lines = overlap_lines
            current_size = sum(len(line) + 1 for line in overlap_lines)
            line_start = i - len(overlap_lines) + 1

    # Remaining lines
    if current_lines:
        text = "\n".join(current_lines)
        chunk_id = hashlib.md5(f"{file_path}:{chunk_index}".encode()).hexdigest()[:16]
        chunks.append({
            "id": chunk_id,
            "text": f"File: {file_path}\nLanguage: {language}\nLines: {line_offset+line_start+1}-{line_offset+len(lines)}\n\n{text}",
            "metadata": {
                "file_path": file_path,
                "language": language,
                "start_line": line_offset + line_start + 1,
                "end_line": line_offset + len(lines),
                "chunk_type": "block",
                "chunk_index": chunk_index,
            }
        })

    return chunks


class CodeParser:
    """Main parser for ZIP files and GitHub repos."""

    def parse_zip(self, zip_bytes: bytes) -> Tuple[List[CodeFile], Dict[str, Any]]:
        """Parse uploaded ZIP file, extract code files."""
        files = []
        stats = {"total_files": 0, "parsed_files": 0, "ignored_files": 0, "total_lines": 0}

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for member in zf.namelist():
                stats["total_files"] += 1

                if should_ignore(member) or member.endswith("/"):
                    stats["ignored_files"] += 1
                    continue

                try:
                    with zf.open(member) as f:
                        raw = f.read()
                        if len(raw) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                            stats["ignored_files"] += 1
                            continue

                        content = raw.decode("utf-8", errors="replace")
                        # Remove null bytes and normalize
                        content = content.replace("\x00", "").strip()
                        if not content:
                            stats["ignored_files"] += 1
                            continue

                        language = detect_language(member)
                        lines = content.count("\n") + 1

                        # Strip leading root folder name for clean paths
                        clean_path = "/".join(member.split("/")[1:]) if "/" in member else member

                        files.append(CodeFile(
                            path=clean_path or member,
                            content=content,
                            language=language,
                            size_bytes=len(raw),
                            lines=lines,
                        ))
                        stats["parsed_files"] += 1
                        stats["total_lines"] += lines

                except Exception as e:
                    logger.warning(f"Failed to parse {member}: {e}")
                    stats["ignored_files"] += 1

        # Limit files
        files = files[:settings.MAX_CONTEXT_FILES]
        return files, stats

    async def parse_github_repo(self, repo_url: str) -> Tuple[List[CodeFile], Dict[str, Any]]:
        """
        Download and parse a GitHub repo as ZIP.
        Supports: https://github.com/user/repo or user/repo
        """
        # Normalize URL
        repo_url = repo_url.strip().rstrip("/")
        if repo_url.startswith("https://github.com/"):
            repo_path = repo_url.replace("https://github.com/", "")
        elif repo_url.startswith("github.com/"):
            repo_path = repo_url.replace("github.com/", "")
        else:
            repo_path = repo_url

        # Extract user/repo (ignore branches/trees)
        parts = repo_path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")

        user, repo = parts[0], parts[1]
        zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/main.zip"

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            try:
                response = await client.get(zip_url)
                if response.status_code == 404:
                    # Try 'master' branch
                    zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/master.zip"
                    response = await client.get(zip_url)

                response.raise_for_status()
                logger.info(f"Downloaded {repo_url}: {len(response.content) / 1024:.1f} KB")
                return self.parse_zip(response.content)

            except httpx.HTTPStatusError as e:
                raise ValueError(f"Could not fetch GitHub repo: {e.response.status_code}")
            except Exception as e:
                raise ValueError(f"Failed to download repo: {str(e)}")

    def build_chunks(self, files: List[CodeFile]) -> List[Dict[str, Any]]:
        """Convert all files to indexed chunks."""
        all_chunks = []
        for code_file in files:
            chunks = smart_chunk_code(
                code_file.content,
                code_file.path,
                code_file.language,
            )
            all_chunks.extend(chunks)
        return all_chunks

    def get_file_tree(self, files: List[CodeFile]) -> List[Dict[str, Any]]:
        """Build a file tree structure for the UI."""
        tree = {}
        for f in files:
            parts = f.path.split("/")
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = {
                "__file__": True,
                "language": f.language,
                "lines": f.lines,
                "size": f.size_bytes,
            }

        return self._flatten_tree(tree)

    def _flatten_tree(self, tree: Dict, prefix: str = "") -> List[Dict]:
        items = []
        for name, value in sorted(tree.items()):
            path = f"{prefix}/{name}" if prefix else name
            if isinstance(value, dict) and "__file__" in value:
                items.append({
                    "name": name,
                    "path": path,
                    "type": "file",
                    "language": value["language"],
                    "lines": value["lines"],
                    "size": value["size"],
                })
            elif isinstance(value, dict):
                items.append({"name": name, "path": path, "type": "directory"})
                items.extend(self._flatten_tree(value, path))
        return items


# Singleton
code_parser = CodeParser()
