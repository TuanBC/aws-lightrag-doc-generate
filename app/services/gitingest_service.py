"""GitIngest service for extracting public GitHub repository content."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class FileChunk:
    """A single file extracted from a repository."""

    file_path: str
    content: str
    estimated_tokens: int


@dataclass
class GitIngestResult:
    """Result from ingesting a GitHub repository."""

    github_url: str
    summary: str
    tree_structure: str
    files: List[FileChunk]
    total_tokens: int


class GitIngestService:
    """Service for extracting public GitHub repository content using file-level chunking."""

    MAX_TOKENS_PER_CHUNK = 4000  # Safe limit for LightRAG
    MAX_FILE_SIZE_KB = 500  # Skip files larger than 500KB to avoid timeout on large repos

    async def ingest_repository(self, github_url: str) -> GitIngestResult:
        """
        Ingest a public GitHub repository by downloading its ZIP archive.

        This method downloads the repository as a ZIP file directly from GitHub,
        avoiding the need for git to be installed (which is problematic in Lambda).

        Args:
            github_url: Public GitHub repository URL

        Returns:
            GitIngestResult with tree structure and file chunks
        """
        import io
        import zipfile

        import httpx

        logger.info(f"Ingesting public repository: {github_url}")

        # Parse GitHub URL to get owner and repo
        owner, repo = self._parse_github_url(github_url)
        if not owner or not repo:
            raise ValueError(f"Invalid GitHub URL: {github_url}")

        # GitHub ZIP download URL (default branch)
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
        alt_zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"

        logger.info(f"Downloading ZIP from: {zip_url}")

        # Download ZIP file
        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            response = await client.get(zip_url)

            # Try master branch if main doesn't exist
            if response.status_code == 404:
                logger.info("Main branch not found, trying master...")
                response = await client.get(alt_zip_url)

            if response.status_code != 200:
                raise RuntimeError(f"Failed to download repository: HTTP {response.status_code}")

            zip_content = response.content
            logger.info(f"Downloaded {len(zip_content) / 1024:.1f} KB")

        # Extract ZIP in memory
        files = []
        tree_lines = []

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            for info in zf.infolist():
                # Skip directories
                if info.is_dir():
                    continue

                # Get relative path (remove the top-level directory name)
                parts = info.filename.split("/", 1)
                if len(parts) < 2:
                    continue
                relative_path = parts[1]

                # Skip empty paths
                if not relative_path:
                    continue

                # Add to tree
                tree_lines.append(relative_path)

                # Skip files that are too large
                if info.file_size > self.MAX_FILE_SIZE_KB * 1024:
                    logger.debug(f"Skipping large file: {relative_path}")
                    continue

                # Skip binary files
                if self._is_binary_file(relative_path):
                    continue

                # Read file content
                try:
                    content = zf.read(info.filename).decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.debug(f"Skipping file {relative_path}: {e}")
                    continue

                # Estimate tokens (~4 chars per token)
                estimated_tokens = len(content) // 4

                # Split large files if needed
                if estimated_tokens > self.MAX_TOKENS_PER_CHUNK:
                    sub_chunks = self._split_large_file(relative_path, content)
                    files.extend(sub_chunks)
                else:
                    files.append(
                        FileChunk(
                            file_path=relative_path,
                            content=content,
                            estimated_tokens=estimated_tokens,
                        )
                    )

        # Build tree structure
        tree_structure = self._build_tree_structure(tree_lines)
        total_tokens = sum(f.estimated_tokens for f in files)

        # Build summary
        summary = f"Repository: {owner}/{repo}\nFiles: {len(files)}\nTotal tokens: {total_tokens}"

        logger.info(f"Parsed {len(files)} files, {total_tokens} tokens")

        return GitIngestResult(
            github_url=github_url,
            summary=summary,
            tree_structure=tree_structure,
            files=files,
            total_tokens=total_tokens,
        )

    def _parse_github_url(self, url: str) -> tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name."""
        # Handle various GitHub URL formats
        patterns = [
            r"github\.com[/:]([^/]+)/([^/]+)",  # https or git@
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2)
                # Remove .git suffix if present
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return owner, repo
        return "", ""

    def _is_binary_file(self, filename: str) -> bool:
        """Check if file is likely binary based on extension."""
        binary_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".bmp",
            ".webp",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".rar",
            ".7z",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".pyc",
            ".pyo",
            ".class",
            ".o",
            ".a",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".otf",
            ".mp3",
            ".mp4",
            ".wav",
            ".avi",
            ".mov",
            ".sqlite",
            ".db",
            ".bin",
        }
        return any(filename.lower().endswith(ext) for ext in binary_extensions)

    def _build_tree_structure(self, file_paths: list[str]) -> str:
        """Build a tree-like structure from file paths."""
        # Sort paths for better readability
        sorted_paths = sorted(file_paths)

        # Simple tree representation
        lines = ["```"]
        for path in sorted_paths[:100]:  # Limit to first 100 files
            depth = path.count("/")
            indent = "  " * depth
            name = path.split("/")[-1]
            lines.append(f"{indent}{name}")

        if len(sorted_paths) > 100:
            lines.append(f"  ... and {len(sorted_paths) - 100} more files")

        lines.append("```")
        return "\n".join(lines)

    def _parse_files(self, content: str) -> List[FileChunk]:
        """
        Parse gitingest content into individual file chunks.

        GitIngest returns content with file markers like:
        ================================================
        FILE: path/to/file.py
        ================================================
        <file content>
        """
        files = []

        # Pattern to match file headers (gitingest uses === separators with FILE:)
        # Using case-insensitive match for FILE/File
        pattern = r"={40,}\n(?:FILE|File): ([^\n]+)\n={40,}\n"
        parts = re.split(pattern, content)

        logger.debug(f"Split content into {len(parts)} parts")

        # Skip first empty part, then pairs of (filename, content)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                file_path = parts[i].strip()
                file_content = parts[i + 1].strip()

                # Estimate tokens (~4 chars per token)
                estimated_tokens = len(file_content) // 4

                # Split large files if needed
                if estimated_tokens > self.MAX_TOKENS_PER_CHUNK:
                    sub_chunks = self._split_large_file(file_path, file_content)
                    files.extend(sub_chunks)
                else:
                    files.append(
                        FileChunk(
                            file_path=file_path,
                            content=file_content,
                            estimated_tokens=estimated_tokens,
                        )
                    )

        logger.info(f"Parsed {len(files)} files from content")
        return files

    def _split_large_file(self, file_path: str, content: str) -> List[FileChunk]:
        """Split large files into smaller chunks with overlap."""
        chunks = []
        max_chars = self.MAX_TOKENS_PER_CHUNK * 4
        overlap = 200  # Character overlap between chunks

        start = 0
        chunk_idx = 0
        while start < len(content):
            end = min(start + max_chars, len(content))
            chunk_content = content[start:end]

            chunks.append(
                FileChunk(
                    file_path=f"{file_path}#chunk{chunk_idx}",
                    content=chunk_content,
                    estimated_tokens=len(chunk_content) // 4,
                )
            )

            # Ensure we always make forward progress
            # Move start forward, using overlap only if there's more content
            if end >= len(content):
                break  # We've reached the end

            # Move forward by (max_chars - overlap) to create overlapping chunks
            start = start + max_chars - overlap
            chunk_idx += 1

        return chunks

    async def ingest_to_lightrag(self, github_url: str) -> dict:
        """
        Ingest a public GitHub repo and embed into LightRAG using file-level chunking.

        Args:
            github_url: Public GitHub repository URL

        Returns:
            Stats about the ingestion
        """
        import traceback

        from app.services.lightrag_service import LightRAGService

        try:
            logger.info(f"Starting ingestion for {github_url}")
            result = await self.ingest_repository(github_url)
            logger.info(f"Parsed {len(result.files)} files from repository")

            lightrag = LightRAGService()

            # Insert tree structure as metadata document
            tree_doc = f"# Repository Structure: {github_url}\n\n{result.tree_structure}"
            await lightrag.insert(content=tree_doc, doc_id=f"{github_url}#tree")
            logger.info("Inserted tree structure")

            # Insert each file as separate document
            inserted_count = 0
            for file_chunk in result.files:
                doc_id = f"{github_url}#{file_chunk.file_path}"
                doc_content = f"# File: {file_chunk.file_path}\n\n{file_chunk.content}"
                await lightrag.insert(content=doc_content, doc_id=doc_id)
                inserted_count += 1
                if inserted_count % 10 == 0:
                    logger.info(f"Inserted {inserted_count}/{len(result.files)} files")

            logger.info(
                f"Completed ingestion: {inserted_count + 1} documents, {result.total_tokens} tokens"
            )

            return {
                "github_url": github_url,
                "summary": result.summary,
                "file_count": len(result.files),
                "total_tokens": result.total_tokens,
                "documents_inserted": inserted_count + 1,  # +1 for tree
            }
        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            logger.error(traceback.format_exc())
            raise
