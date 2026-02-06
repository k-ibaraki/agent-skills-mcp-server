"""Unit tests for tools module.

This module tests the functionality of file_read, file_write, shell, and web_fetch tools.
Focuses on normal operation, error handling, and edge cases.
"""

from unittest.mock import Mock, patch

import httpx
import pytest

from agent_skills_mcp.tools import file_read, file_write, shell, web_fetch


@pytest.mark.unit
class TestFileRead:
    """Test file_read tool functionality."""

    def test_read_existing_file(self, temp_skills_dir, sample_skill_file, monkeypatch):
        """Test reading an existing file."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(sample_skill_file))
        assert result == "Sample skill content"

    def test_read_nonexistent_file(self, temp_skills_dir, monkeypatch):
        """Test reading a nonexistent file."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(temp_skills_dir / "nonexistent.txt"))
        assert "Error: File not found" in result

    def test_read_directory(self, temp_skills_dir, monkeypatch):
        """Test that reading a directory returns error."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(temp_skills_dir))
        assert "Error: Not a file" in result

    def test_read_empty_file(self, temp_skills_dir, monkeypatch):
        """Test reading an empty file."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        empty_file = temp_skills_dir / "empty.txt"
        empty_file.write_text("")

        result = file_read(str(empty_file))
        assert result == ""

    def test_read_utf8_content(self, temp_skills_dir, monkeypatch):
        """Test reading UTF-8 content with special characters."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        utf8_file = temp_skills_dir / "utf8.txt"
        # Note: \r is normalized to \n in text mode on Unix systems
        content = "日本語 テスト 🎉 Special: \n\t"
        utf8_file.write_text(content, encoding="utf-8")

        result = file_read(str(utf8_file))
        assert result == content

    def test_read_large_file(self, temp_skills_dir, monkeypatch):
        """Test reading a large file."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        large_file = temp_skills_dir / "large.txt"
        large_content = "x" * 1_000_000  # 1MB
        large_file.write_text(large_content)

        result = file_read(str(large_file))
        assert result == large_content

    def test_read_with_relative_path(self, temp_skills_dir, monkeypatch):
        """Test reading with relative path within allowed directory."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        # Create nested structure
        nested_dir = temp_skills_dir / "subdir"
        nested_dir.mkdir()
        test_file = nested_dir / "test.txt"
        test_file.write_text("Nested content")

        result = file_read(str(test_file))
        assert result == "Nested content"

    @patch(
        "pathlib.Path.read_text", side_effect=PermissionError("Mock permission denied")
    )
    def test_read_permission_error(self, mock_read_text, temp_skills_dir, monkeypatch):
        """Test handling of permission error."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "test.txt"
        test_file.write_text("content")

        result = file_read(str(test_file))
        assert "Error: Permission denied" in result

    @patch(
        "pathlib.Path.read_text",
        side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "Mock error"),
    )
    def test_read_unicode_error(self, mock_read_text, temp_skills_dir, monkeypatch):
        """Test handling of Unicode decode error."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "test.txt"
        test_file.write_text("content")

        result = file_read(str(test_file))
        assert "Error reading file" in result


@pytest.mark.unit
class TestFileWrite:
    """Test file_write tool functionality."""

    def test_write_new_file(self, temp_skills_dir, monkeypatch):
        """Test writing a new file."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "new.txt"
        content = "New file content"

        result = file_write(str(test_file), content)
        assert "Successfully wrote" in result
        assert "16 characters" in result
        assert test_file.read_text() == content

    def test_write_overwrite_existing(
        self, temp_skills_dir, sample_skill_file, monkeypatch
    ):
        """Test overwriting an existing file."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        new_content = "Overwritten content"
        result = file_write(str(sample_skill_file), new_content)
        assert "Successfully wrote" in result
        assert sample_skill_file.read_text() == new_content

    def test_write_empty_content(self, temp_skills_dir, monkeypatch):
        """Test writing empty content."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "empty.txt"
        result = file_write(str(test_file), "")
        assert "Successfully wrote 0 characters" in result
        assert test_file.read_text() == ""

    def test_write_utf8_content(self, temp_skills_dir, monkeypatch):
        """Test writing UTF-8 content with special characters."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "utf8.txt"
        # Note: \r is normalized to \n in text mode on Unix systems
        content = "日本語 テスト 🎉 Special: \n\t"

        result = file_write(str(test_file), content)
        assert "Successfully wrote" in result
        assert test_file.read_text(encoding="utf-8") == content

    def test_write_large_content(self, temp_skills_dir, monkeypatch):
        """Test writing large content."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "large.txt"
        content = "x" * 1_000_000  # 1MB

        result = file_write(str(test_file), content)
        assert "Successfully wrote 1000000 characters" in result
        assert test_file.read_text() == content

    def test_write_creates_nested_directories(self, temp_skills_dir, monkeypatch):
        """Test that parent directories are created."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        nested_file = temp_skills_dir / "a" / "b" / "c" / "file.txt"
        result = file_write(str(nested_file), "nested")
        assert "Successfully wrote" in result
        assert nested_file.exists()
        assert nested_file.read_text() == "nested"

    @patch(
        "pathlib.Path.write_text", side_effect=PermissionError("Mock permission denied")
    )
    def test_write_permission_error(
        self, mock_write_text, temp_skills_dir, monkeypatch
    ):
        """Test handling of permission error."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "test.txt"
        result = file_write(str(test_file), "content")
        assert "Error: Permission denied" in result

    @patch("pathlib.Path.write_text", side_effect=Exception("Mock error"))
    def test_write_generic_error(self, mock_write_text, temp_skills_dir, monkeypatch):
        """Test handling of generic error."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "test.txt"
        result = file_write(str(test_file), "content")
        assert "Error writing file" in result


@pytest.mark.unit
class TestShell:
    """Test shell tool functionality."""

    def test_simple_command(self):
        """Test executing a simple command."""
        result = shell("echo 'test'")
        assert "test" in result

    def test_command_with_output(self):
        """Test command that produces output."""
        result = shell("echo 'line1' && echo 'line2'")
        assert "line1" in result
        assert "line2" in result

    def test_command_with_stderr(self):
        """Test command that outputs to stderr."""
        result = shell("echo 'error' >&2")
        assert "error" in result or "[stderr]" in result

    def test_command_with_nonzero_exit(self):
        """Test command that exits with non-zero status."""
        result = shell("exit 42")
        assert "[exit code]: 42" in result

    def test_command_no_output(self):
        """Test command with no output."""
        result = shell("true")
        assert result == "(no output)" or "[exit code]" not in result

    def test_pipe_commands(self):
        """Test piped commands."""
        result = shell("echo 'test' | cat")
        assert "test" in result

    def test_command_chaining(self):
        """Test command chaining with semicolon."""
        result = shell("echo 'first'; echo 'second'")
        assert "first" in result
        assert "second" in result

    def test_invalid_command(self):
        """Test executing invalid command."""
        result = shell("nonexistent_command_xyz123")
        assert "[exit code]" in result or "not found" in result.lower()

    def test_command_with_special_chars(self):
        """Test command with special characters."""
        result = shell("echo 'Special: $HOME @ 100% #1'")
        assert "Special:" in result

    @patch("subprocess.run", side_effect=Exception("Mock subprocess error"))
    def test_subprocess_exception(self, mock_run):
        """Test handling of subprocess exception."""
        result = shell("echo test")
        assert "Error executing command" in result
        assert "Mock subprocess error" in result


@pytest.mark.unit
class TestWebFetch:
    """Test web_fetch tool functionality."""

    @pytest.mark.asyncio
    async def test_get_html_content(self):
        """Test fetching HTML content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.content = mock_response.text.encode()

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await web_fetch("https://example.com")
            assert "Test content" in result

    @pytest.mark.asyncio
    async def test_get_json_content(self):
        """Test fetching JSON content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = mock_response.text.encode()

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await web_fetch("https://api.example.com/data")
            assert '"key": "value"' in result

    @pytest.mark.asyncio
    async def test_get_text_content(self):
        """Test fetching plain text content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Plain text content"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = mock_response.text.encode()

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await web_fetch("https://example.com/file.txt")
            assert "Plain text content" in result

    @pytest.mark.asyncio
    async def test_get_binary_content(self):
        """Test fetching binary content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.content = b"\x00\x01\x02\x03"

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await web_fetch("https://example.com/file.bin")
            assert "Content type application/octet-stream received" in result
            assert "Size: 4 bytes" in result

    @pytest.mark.asyncio
    async def test_post_with_json_body(self):
        """Test POST request with JSON body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = mock_response.text.encode()

        with patch(
            "httpx.AsyncClient.request", return_value=mock_response
        ) as mock_request:
            result = await web_fetch(
                "https://api.example.com/create",
                method="POST",
                body='{"name": "test"}',
            )
            assert "success" in result
            # Verify JSON was parsed and sent
            assert mock_request.called
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["method"] == "POST"
            assert call_kwargs["json"] == {"name": "test"}

    @pytest.mark.asyncio
    async def test_post_with_text_body(self):
        """Test POST request with text body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = mock_response.text.encode()

        with patch(
            "httpx.AsyncClient.request", return_value=mock_response
        ) as mock_request:
            result = await web_fetch(
                "https://api.example.com/create",
                method="POST",
                body="plain text data",
            )
            assert "OK" in result
            # Verify text was sent as content
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["content"] == "plain text data"

    @pytest.mark.asyncio
    async def test_get_with_headers(self):
        """Test GET request with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Protected content"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = mock_response.text.encode()

        with patch(
            "httpx.AsyncClient.request", return_value=mock_response
        ) as mock_request:
            result = await web_fetch(
                "https://api.example.com/protected",
                headers={"Authorization": "Bearer token123"},
            )
            assert "Protected content" in result
            # Verify headers were sent
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer token123"

    @pytest.mark.asyncio
    async def test_get_with_params(self):
        """Test GET request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Search results"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = mock_response.text.encode()

        with patch(
            "httpx.AsyncClient.request", return_value=mock_response
        ) as mock_request:
            result = await web_fetch(
                "https://api.example.com/search",
                params={"q": "test", "limit": "10"},
            )
            assert "Search results" in result
            # Verify params were sent
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"] == {"q": "test", "limit": "10"}

    @pytest.mark.asyncio
    async def test_header_env_var_expansion(self, monkeypatch):
        """Test environment variable expansion in headers."""
        monkeypatch.setenv("API_TOKEN", "secret123")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = mock_response.text.encode()

        with patch(
            "httpx.AsyncClient.request", return_value=mock_response
        ) as mock_request:
            result = await web_fetch(
                "https://api.example.com",
                headers={"Authorization": "Bearer ${API_TOKEN}"},
            )
            assert "OK" in result
            # Verify env var was expanded
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer secret123"

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Test handling of timeout error."""
        with patch(
            "httpx.AsyncClient.request",
            side_effect=httpx.TimeoutException("Mock timeout"),
        ):
            result = await web_fetch("https://slow.example.com")
            assert "Error: Request to https://slow.example.com timed out" in result

    @pytest.mark.asyncio
    async def test_http_status_error(self):
        """Test handling of HTTP error status."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.url = "https://example.com/notfound"

        with patch(
            "httpx.AsyncClient.request",
            side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=mock_response,
            ),
        ):
            result = await web_fetch("https://example.com/notfound")
            assert "Error: HTTP 404" in result

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        """Test handling of generic exception."""
        with patch(
            "httpx.AsyncClient.request",
            side_effect=Exception("Mock network error"),
        ):
            result = await web_fetch("https://example.com")
            assert "Error fetching URL" in result
            assert "Mock network error" in result

    @pytest.mark.asyncio
    async def test_content_truncation(self):
        """Test that large content is truncated."""
        # Create content larger than 100KB
        large_content = "x" * 150_000

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = large_content
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = large_content.encode()

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await web_fetch("https://example.com/large.html")
            assert len(result) < 150_000
            assert "content truncated at 100KB" in result
