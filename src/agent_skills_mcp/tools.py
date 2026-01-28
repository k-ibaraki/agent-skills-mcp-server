"""Tools for Agent Skills execution with Strands Agents.

This module provides tools for skill execution:
- file_read, file_write, shell: Wrapped from strands-agents-tools package
- web_fetch: Custom implementation (not provided by strands-agents-tools)
"""

import logging
from pathlib import Path

import httpx
from strands import tool

logger = logging.getLogger(__name__)


@tool
def file_read(path: str) -> str:
    """Read contents from a file.

    Args:
        path: Absolute or relative path to the file to read.

    Returns:
        The contents of the file as a string.
    """
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"Error: File not found: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"

        content = file_path.read_text(encoding="utf-8")
        return content
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        logger.error(f"file_read failed for {path}: {e}")
        return f"Error reading file: {e}"


@tool
def file_write(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: Absolute or relative path to the file to write.
        content: Content to write to the file.

    Returns:
        Success or error message.
    """
    try:
        file_path = Path(path).expanduser().resolve()

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        logger.error(f"file_write failed for {path}: {e}")
        return f"Error writing file: {e}"


@tool
def shell(command: str) -> str:
    """Execute a shell command.

    Args:
        command: Shell command to execute.

    Returns:
        Command output (stdout and stderr combined).
    """
    import subprocess

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
        )

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"

        if result.returncode != 0:
            output += f"\n[exit code]: {result.returncode}"

        return output if output else "(no output)"

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        logger.error(f"shell command failed: {e}")
        return f"Error executing command: {e}"


@tool
async def web_fetch(url: str, prompt: str | None = None) -> str:
    """Fetch content from a URL.

    Args:
        url: URL to fetch content from.
        prompt: Optional prompt describing what information to extract.

    Returns:
        Content from the URL or error message.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Get content type
            content_type = response.headers.get("content-type", "")

            # For HTML, return text content
            if "text/html" in content_type:
                content = response.text
                # Limit content size to avoid context overflow
                if len(content) > 50000:
                    content = content[:50000] + "\n... (content truncated)"
                return content
            elif "application/json" in content_type:
                return response.text
            elif "text/" in content_type:
                return response.text
            else:
                return f"Content type {content_type} received. Size: {len(response.content)} bytes"

    except httpx.TimeoutException:
        return f"Error: Request to {url} timed out"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} for {url}"
    except Exception as e:
        logger.error(f"web_fetch failed for {url}: {e}")
        return f"Error fetching URL: {e}"


__all__ = ["file_read", "file_write", "shell", "web_fetch"]
