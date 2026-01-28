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

# Allowed directories for file operations (security restriction)
ALLOWED_DIRECTORIES = [
    Path("skills").absolute(),
    Path(".tmp").absolute(),
]


def _is_path_allowed(path: Path) -> bool:
    """Check if path is within allowed directories.

    Args:
        path: Path to check.

    Returns:
        True if path is within allowed directories, False otherwise.
    """
    try:
        resolved_path = path.resolve()
        return any(
            resolved_path == allowed or allowed in resolved_path.parents
            for allowed in ALLOWED_DIRECTORIES
        )
    except (OSError, RuntimeError):
        # Handle cases where path cannot be resolved
        return False


@tool
def file_read(path: str) -> str:
    """Read contents from a file.

    For security, only files within allowed directories can be read:
    - skills/ (skill files)
    - .tmp/ (temporary files)

    Args:
        path: Absolute or relative path to the file to read.

    Returns:
        The contents of the file as a string.
    """
    try:
        file_path = Path(path).expanduser()

        # Security check: verify path is within allowed directories
        if not _is_path_allowed(file_path):
            allowed_dirs = ", ".join(str(d) for d in ALLOWED_DIRECTORIES)
            return f"Error: Access denied. File must be within allowed directories: {allowed_dirs}"

        file_path = file_path.resolve()

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

    For security, only files within allowed directories can be written:
    - skills/ (skill files)
    - .tmp/ (temporary files)

    Args:
        path: Absolute or relative path to the file to write.
        content: Content to write to the file.

    Returns:
        Success or error message.
    """
    try:
        file_path = Path(path).expanduser()

        # Security check: verify path is within allowed directories
        if not _is_path_allowed(file_path):
            allowed_dirs = ", ".join(str(d) for d in ALLOWED_DIRECTORIES)
            return f"Error: Access denied. File must be within allowed directories: {allowed_dirs}"

        file_path = file_path.resolve()

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
async def web_fetch(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    body: str | None = None,
    prompt: str | None = None,
) -> str:
    """Fetch content from a URL with optional headers, params, and body.

    Note: Large responses are automatically managed by the conversation manager
    through summarization to prevent context window overflow.

    Args:
        url: URL to fetch content from.
        method: HTTP method (GET, POST, PUT, DELETE, etc.). Default is GET.
        headers: Optional dictionary of HTTP headers. Supports environment variable expansion
                using ${VAR_NAME} syntax (e.g., {"Authorization": "Bearer ${API_TOKEN}"}).
        params: Optional dictionary of query parameters to append to the URL.
        body: Optional request body (for POST, PUT, etc.).
        prompt: Optional prompt describing what information to extract (deprecated, unused).

    Returns:
        Content from the URL or error message.

    Examples:
        # Simple GET request
        web_fetch("https://api.example.com/data")

        # GET with query parameters
        web_fetch("https://api.example.com/search", params={"q": "test", "limit": "10"})

        # GET with authentication header (using environment variable)
        web_fetch(
            "https://api.example.com/protected",
            headers={"Authorization": "Bearer ${API_TOKEN}"}
        )

        # POST with JSON body
        web_fetch(
            "https://api.example.com/create",
            method="POST",
            headers={"Content-Type": "application/json"},
            body='{"name": "test"}'
        )
    """
    import json
    import os
    import re

    try:
        # Debug logging
        logger.debug(f"web_fetch called with url={url}, headers={headers}")

        # Expand environment variables in headers
        expanded_headers = {}
        if headers:
            for key, value in headers.items():
                # Clean up header key and value (remove extra quotes if present)
                clean_key = str(key).strip().strip('"').strip("'")
                clean_value = str(value).strip()

                # Replace ${VAR_NAME} with environment variable value
                expanded_value = re.sub(
                    r"\$\{([^}]+)\}",
                    lambda m: os.getenv(m.group(1), m.group(0)),
                    clean_value,
                )
                expanded_headers[clean_key] = expanded_value

        logger.debug(f"Expanded headers: {expanded_headers}")

        # Prepare request kwargs
        request_kwargs = {
            "method": method.upper(),
            "url": url,
            "headers": expanded_headers if expanded_headers else None,
            "params": params,
        }

        # Add body for methods that support it
        if body and method.upper() in ["POST", "PUT", "PATCH"]:
            # Try to parse as JSON, otherwise send as text
            try:
                request_kwargs["json"] = json.loads(body)
            except json.JSONDecodeError:
                request_kwargs["content"] = body

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.request(**request_kwargs)
            response.raise_for_status()

            # Get content type
            content_type = response.headers.get("content-type", "")

            # For HTML, return text content with size limit
            if "text/html" in content_type:
                content = response.text
                # Limit content size to prevent excessive memory usage
                if len(content) > 100000:
                    content = content[:100000] + "\n... (content truncated at 100KB)"
                return content
            elif "application/json" in content_type:
                content = response.text
                if len(content) > 100000:
                    content = content[:100000] + "\n... (content truncated at 100KB)"
                return content
            elif "text/" in content_type:
                content = response.text
                if len(content) > 100000:
                    content = content[:100000] + "\n... (content truncated at 100KB)"
                return content
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
