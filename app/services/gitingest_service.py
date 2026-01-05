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
        Ingest a public GitHub repository and extract file-level chunks.

        Args:
            github_url: Public GitHub repository URL

        Returns:
            GitIngestResult with tree structure and file chunks
        """
        import asyncio
        import os
        import shutil
        import subprocess
        import traceback

        from gitingest import ingest

        logger.info(f"Ingesting public repository: {github_url}")

        # Debug: Check if git is available
        git_path = shutil.which("git")
        logger.info(f"Git path: {git_path}")

        if not git_path:
            # Try to find git in common locations
            for path in ["/usr/bin/git", "/usr/local/bin/git"]:
                if os.path.exists(path):
                    git_path = path
                    break

        if not git_path:
            raise RuntimeError("Git is not installed or not in PATH")

        # Test git version
        try:
            result = subprocess.run(
                [git_path, "--version"], capture_output=True, text=True, timeout=10
            )
            logger.info(f"Git version: {result.stdout.strip()}")
        except Exception as e:
            logger.error(f"Failed to run git: {e}")
            raise RuntimeError(f"Git is not working: {e}")

        # Log environment for debugging
        logger.info(f"TMPDIR: {os.environ.get('TMPDIR', 'not set')}")
        logger.info(f"HOME: {os.environ.get('HOME', 'not set')}")

        try:
            # Use sync version with to_thread for Windows compatibility
            # (ingest_async has subprocess issues on Windows event loop)
            # Limit file size to avoid timeout on large repos
            max_file_size_bytes = self.MAX_FILE_SIZE_KB * 1024
            summary, tree, content = await asyncio.to_thread(
                ingest, github_url, max_file_size=max_file_size_bytes
            )
        except Exception as e:
            logger.error(f"Gitingest failed: {e}")
            logger.error(traceback.format_exc())
            raise

        # Parse content into file-level chunks
        files = self._parse_files(content)
        total_tokens = sum(f.estimated_tokens for f in files)

        return GitIngestResult(
            github_url=github_url,
            summary=summary,
            tree_structure=tree,
            files=files,
            total_tokens=total_tokens,
        )

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
