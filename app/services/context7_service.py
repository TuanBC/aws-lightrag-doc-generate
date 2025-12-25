"""Context7 MCP client for fetching up-to-date library documentation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LibraryInfo:
    """Library information from Context7."""

    library_id: str
    name: str
    description: Optional[str] = None


@dataclass
class LibraryDocs:
    """Documentation content from Context7."""

    library_id: str
    topic: Optional[str]
    content: str
    page: int


class Context7Service:
    """
    Client for Context7 remote MCP server.

    Context7 provides up-to-date documentation for libraries and frameworks.
    Uses the remote MCP endpoint at https://mcp.context7.com/mcp
    """

    def __init__(
        self,
        mcp_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        settings = get_settings()
        self.mcp_url = mcp_url or settings.context7_mcp_url
        self.api_key = api_key or settings.context7_api_key
        self.timeout = timeout

        # Build headers
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["CONTEXT7_API_KEY"] = self.api_key

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a Context7 MCP tool via HTTP.

        Context7 MCP exposes tools via a JSON-RPC-like interface.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.mcp_url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    raise Context7Error(f"MCP error: {result['error']}")

                return result.get("result", {})

            except httpx.HTTPStatusError as e:
                logger.error(f"Context7 HTTP error: {e}")
                raise Context7Error(f"HTTP error: {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error(f"Context7 request error: {e}")
                raise Context7Error(f"Request error: {str(e)}") from e

    async def resolve_library_id(self, library_name: str) -> List[LibraryInfo]:
        """
        Resolve a library name to Context7-compatible library IDs.

        Args:
            library_name: Name of the library to search for (e.g., "react", "fastapi")

        Returns:
            List of matching library info objects
        """
        logger.info(f"Resolving library ID for: {library_name}")

        result = await self._call_tool(
            "resolve-library-id",
            {"libraryName": library_name},
        )

        # Parse result content
        libraries = []
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        # Parse the text content which contains library info
                        text = item.get("text", "")
                        libraries.extend(self._parse_library_list(text))

        return libraries

    def _parse_library_list(self, text: str) -> List[LibraryInfo]:
        """Parse library list from Context7 response text."""
        libraries = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("/"):
                # Format: /org/repo - description
                parts = line.split(" - ", 1)
                library_id = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else None

                libraries.append(
                    LibraryInfo(
                        library_id=library_id,
                        name=library_id.split("/")[-1],
                        description=description,
                    )
                )

        return libraries

    async def get_library_docs(
        self,
        library_id: str,
        topic: Optional[str] = None,
        page: int = 1,
    ) -> LibraryDocs:
        """
        Fetch documentation for a library.

        Args:
            library_id: Context7-compatible library ID (e.g., "/vercel/next.js")
            topic: Optional topic to focus docs on (e.g., "routing", "hooks")
            page: Page number for pagination (1-10)

        Returns:
            Library documentation content
        """
        logger.info(f"Fetching docs for {library_id}, topic={topic}, page={page}")

        arguments = {"context7CompatibleLibraryID": library_id}
        if topic:
            arguments["topic"] = topic
        if page > 1:
            arguments["page"] = page

        result = await self._call_tool("get-library-docs", arguments)

        # Extract content from result
        content = ""
        if isinstance(result, dict) and "content" in result:
            content_items = result["content"]
            if isinstance(content_items, list):
                content_parts = []
                for item in content_items:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content_parts.append(item.get("text", ""))
                content = "\n".join(content_parts)

        return LibraryDocs(
            library_id=library_id,
            topic=topic,
            content=content,
            page=page,
        )

    async def get_full_library_context(
        self,
        library_name: str,
        topics: Optional[List[str]] = None,
        max_pages: int = 3,
    ) -> str:
        """
        Get comprehensive documentation for a library.

        This method resolves the library ID, then fetches docs for specified topics.

        Args:
            library_name: Human-readable library name
            topics: List of topics to fetch docs for
            max_pages: Maximum pages to fetch per topic

        Returns:
            Combined documentation string
        """
        # Resolve library ID
        libraries = await self.resolve_library_id(library_name)
        if not libraries:
            return f"No documentation found for library: {library_name}"

        # Use first matching library
        library = libraries[0]
        logger.info(f"Using library: {library.library_id}")

        all_docs = []
        all_docs.append(f"# {library.name} Documentation")
        if library.description:
            all_docs.append(f"\n{library.description}\n")

        # Fetch general docs first
        general_docs = await self.get_library_docs(library.library_id)
        all_docs.append(f"\n## Overview\n\n{general_docs.content}")

        # Fetch topic-specific docs
        if topics:
            for topic in topics:
                try:
                    topic_docs = await self.get_library_docs(
                        library.library_id,
                        topic=topic,
                    )
                    if topic_docs.content:
                        all_docs.append(f"\n## {topic.title()}\n\n{topic_docs.content}")
                except Context7Error as e:
                    logger.warning(f"Failed to fetch {topic} docs: {e}")

        return "\n".join(all_docs)


class Context7Error(Exception):
    """Error from Context7 MCP service."""

    pass
