"""Security tests for tools module.

This module tests security aspects of file_read, file_write, and shell tools:
- Path traversal attack prevention
- Symlink escape prevention
- Shell injection prevention
- Timeout enforcement
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_skills_mcp.tools import _is_path_allowed, file_read, file_write, shell


@pytest.mark.unit
class TestPathTraversalPrevention:
    """Test path traversal attack prevention in file operations."""

    def test_relative_path_traversal_skills(self, temp_skills_dir):
        """Test that relative path traversal from skills/ is blocked."""
        # Try to escape skills directory using ../
        result = file_read("skills/../../../etc/passwd")
        assert "Error: Access denied" in result
        assert "allowed directories" in result.lower()

    def test_relative_path_traversal_nested(self, temp_skills_dir):
        """Test that nested path traversal is blocked."""
        result = file_read("skills/skill-name/../../.env")
        assert "Error: Access denied" in result

    def test_absolute_path_etc_passwd(self):
        """Test that absolute path to /etc/passwd is blocked."""
        result = file_read("/etc/passwd")
        assert "Error: Access denied" in result

    def test_absolute_path_tmp(self):
        """Test that absolute path outside allowed dirs is blocked."""
        result = file_read("/tmp/malicious.txt")
        assert "Error: Access denied" in result

    def test_home_directory_escape(self):
        """Test that home directory (~/) access is blocked."""
        result = file_read("~/.ssh/id_rsa")
        assert "Error: Access denied" in result

    def test_current_directory_escape(self):
        """Test that current directory (./) escape is blocked."""
        result = file_read("./../../.env")
        assert "Error: Access denied" in result

    def test_allowed_skills_directory_read(
        self, temp_skills_dir, sample_skill_file, monkeypatch
    ):
        """Test that reading from allowed skills/ directory works."""
        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir.parent / "skills", temp_skills_dir.parent / ".tmp"],
        )
        result = file_read(str(sample_skill_file))
        assert result == "Sample skill content"

    def test_allowed_tmp_directory_read(self, temp_tmp_dir, monkeypatch):
        """Test that reading from allowed .tmp/ directory works."""
        # Create a test file in .tmp
        test_file = temp_tmp_dir / "test.txt"
        test_file.write_text("Temporary content")

        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_tmp_dir.parent / "skills", temp_tmp_dir],
        )

        result = file_read(str(test_file))
        assert result == "Temporary content"

    def test_path_with_null_bytes(self):
        """Test that paths with null bytes are rejected."""
        result = file_read("skills/skill\x00/../../etc/passwd")
        # Python path resolution handles null bytes, should still be blocked
        assert "Error: Access denied" in result or "Error" in result

    def test_windows_style_path_traversal(self):
        """Test that Windows-style path traversal is blocked."""
        result = file_read("skills\\..\\..\\..\\etc\\passwd")
        assert "Error: Access denied" in result or "Error" in result


@pytest.mark.unit
class TestSymlinkEscapePrevention:
    """Test symlink escape prevention in file operations."""

    def test_symlink_to_etc_passwd(self, temp_skills_dir, monkeypatch):
        """Test that symlink to /etc/passwd is blocked."""
        # Create a symlink pointing outside allowed directory
        symlink_path = temp_skills_dir / "malicious_link"
        try:
            symlink_path.symlink_to("/etc/passwd")
        except (OSError, NotImplementedError):
            # On some systems, creating symlinks requires special permissions
            pytest.skip("Cannot create symlinks on this system")

        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(symlink_path))
        assert "Error: Access denied" in result

    def test_symlink_to_parent_directory(self, temp_skills_dir, monkeypatch):
        """Test that symlink to parent directory is blocked."""
        # Create a symlink pointing to parent directory
        symlink_path = temp_skills_dir / "parent_link"
        try:
            symlink_path.symlink_to(temp_skills_dir.parent)
        except (OSError, NotImplementedError):
            pytest.skip("Cannot create symlinks on this system")

        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(symlink_path))
        # Symlink to directory should either be blocked or return "Not a file"
        assert "Error: Access denied" in result or "Error: Not a file" in result

    def test_symlink_within_allowed_directory(self, temp_skills_dir, monkeypatch):
        """Test that symlink within allowed directory is permitted."""
        # Create a file and a symlink within skills directory
        target_file = temp_skills_dir / "target.txt"
        target_file.write_text("Target content")
        symlink_path = temp_skills_dir / "link.txt"
        try:
            symlink_path.symlink_to(target_file)
        except (OSError, NotImplementedError):
            pytest.skip("Cannot create symlinks on this system")

        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(symlink_path))
        assert result == "Target content"

    def test_broken_symlink(self, temp_skills_dir, monkeypatch):
        """Test that broken symlink is handled gracefully."""
        symlink_path = temp_skills_dir / "broken_link"
        try:
            symlink_path.symlink_to(temp_skills_dir / "nonexistent.txt")
        except (OSError, NotImplementedError):
            pytest.skip("Cannot create symlinks on this system")

        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        result = file_read(str(symlink_path))
        assert "Error: File not found" in result


@pytest.mark.unit
class TestFileWriteSecurity:
    """Test security aspects of file_write tool."""

    def test_write_path_traversal_blocked(self):
        """Test that path traversal in write operations is blocked."""
        result = file_write("skills/../../../tmp/malicious.txt", "malicious content")
        assert "Error: Access denied" in result

    def test_write_absolute_path_blocked(self):
        """Test that absolute path write is blocked."""
        result = file_write("/tmp/malicious.txt", "malicious content")
        assert "Error: Access denied" in result

    def test_write_to_allowed_directory(self, temp_skills_dir, monkeypatch):
        """Test that writing to allowed directory works."""
        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_file = temp_skills_dir / "new_file.txt"
        result = file_write(str(test_file), "New content")
        assert "Successfully wrote" in result
        assert test_file.read_text() == "New content"

    def test_write_creates_parent_directories(self, temp_skills_dir, monkeypatch):
        """Test that write creates parent directories within allowed dirs."""
        # Patch ALLOWED_DIRECTORIES to use temp directory
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        nested_file = temp_skills_dir / "subdir1" / "subdir2" / "file.txt"
        result = file_write(str(nested_file), "Nested content")
        assert "Successfully wrote" in result
        assert nested_file.exists()
        assert nested_file.read_text() == "Nested content"


@pytest.mark.unit
class TestShellInjectionPrevention:
    """Test shell injection prevention in shell tool."""

    def test_shell_semicolon_command_chaining(self):
        """Test that semicolon command chaining is executed (shell=True behavior)."""
        # Note: shell=True allows command chaining. This test documents current behavior.
        # In production, consider using shell=False with explicit command lists.
        result = shell("echo 'first'; echo 'second'")
        assert "first" in result
        assert "second" in result

    def test_shell_pipe_command(self):
        """Test that pipe commands work (shell=True behavior)."""
        result = shell("echo 'test' | cat")
        assert "test" in result

    def test_shell_invalid_command(self):
        """Test that invalid commands return error exit code."""
        result = shell("nonexistent_command_12345")
        assert "[exit code]" in result

    @patch("subprocess.run")
    def test_shell_timeout_enforced(self, mock_run):
        """Test that 30 second timeout is enforced."""
        # Mock subprocess.run to raise TimeoutExpired
        mock_run.side_effect = subprocess.TimeoutExpired("sleep 60", 30)

        result = shell("sleep 60")
        assert "Error: Command timed out after 30 seconds" in result

    @patch("subprocess.run")
    def test_shell_timeout_parameter(self, mock_run):
        """Test that timeout parameter is passed to subprocess.run."""
        mock_run.return_value = subprocess.CompletedProcess(
            args="echo test",
            returncode=0,
            stdout="test",
            stderr="",
        )

        shell("echo test")
        # Verify that timeout=30 was passed
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["timeout"] == 30

    def test_shell_stdout_stderr_captured(self):
        """Test that both stdout and stderr are captured."""
        # Use a command that outputs to both stdout and stderr
        result = shell("echo 'stdout' && echo 'stderr' >&2")
        assert "stdout" in result
        assert "stderr" in result or "[stderr]" in result

    @patch("subprocess.run")
    def test_shell_exception_handling(self, mock_run):
        """Test that exceptions are handled gracefully."""
        mock_run.side_effect = Exception("Mock error")

        result = shell("echo test")
        assert "Error executing command" in result
        assert "Mock error" in result


@pytest.mark.unit
class TestIsPathAllowed:
    """Test the _is_path_allowed helper function."""

    def test_path_in_skills_directory(self, temp_skills_dir, monkeypatch):
        """Test that path within skills/ is allowed."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        test_path = temp_skills_dir / "test.txt"
        assert _is_path_allowed(test_path) is True

    def test_path_in_tmp_directory(self, temp_tmp_dir, monkeypatch):
        """Test that path within .tmp/ is allowed."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_tmp_dir.parent / "skills", temp_tmp_dir],
        )

        test_path = temp_tmp_dir / "test.txt"
        assert _is_path_allowed(test_path) is True

    def test_path_outside_allowed_directories(self):
        """Test that path outside allowed directories is denied."""
        test_path = Path("/etc/passwd")
        assert _is_path_allowed(test_path) is False

    def test_path_resolution_failure(self, monkeypatch):
        """Test that path resolution failure is handled."""
        # Create a path that cannot be resolved
        with patch.object(Path, "resolve", side_effect=OSError("Mock error")):
            test_path = Path("invalid/path")
            assert _is_path_allowed(test_path) is False

    def test_path_with_parent_components(self, temp_skills_dir, monkeypatch):
        """Test that path with ../ components is correctly validated."""
        monkeypatch.setattr(
            "agent_skills_mcp.tools.ALLOWED_DIRECTORIES",
            [temp_skills_dir, temp_skills_dir.parent / ".tmp"],
        )

        # Create nested directory
        nested_dir = temp_skills_dir / "subdir1" / "subdir2"
        nested_dir.mkdir(parents=True)

        # Path with ../ that stays within allowed directory
        test_path = nested_dir / ".." / "file.txt"
        assert _is_path_allowed(test_path) is True

        # Path with ../ that escapes allowed directory
        escape_path = temp_skills_dir / ".." / "etc" / "passwd"
        assert _is_path_allowed(escape_path) is False
