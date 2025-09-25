#!/usr/bin/env python3
"""
Claude Code Post-Edit Hook for nf-core/tools

This hook runs after file edits to automatically:
1. Run tests for edited test files
2. Run related tests for edited source files
3. Run linting and type checking on Python files

Uses uv for all Python operations per project conventions.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120  # 2 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out: {' '.join(cmd)}"
    except Exception as e:
        return 1, "", f"Failed to run command {' '.join(cmd)}: {str(e)}"


def find_related_test_file(source_file: Path, project_root: Path) -> Optional[Path]:
    """Find the corresponding test file for a source file"""
    # Convert source path to test path
    # e.g., nf_core/modules/install.py -> tests/modules/test_install.py

    try:
        # Get relative path from project root
        rel_path = source_file.relative_to(project_root)

        # Skip if not in nf_core directory
        if not rel_path.parts or rel_path.parts[0] != "nf_core":
            return None

        # Build test path
        parts = list(rel_path.parts[1:])  # Remove 'nf_core' prefix
        if not parts:
            return None

        # Convert filename: install.py -> test_install.py
        filename = parts[-1]
        if filename.endswith('.py'):
            test_filename = f"test_{filename}"
            parts[-1] = test_filename

            # Build full test path: tests/modules/test_install.py
            test_path = project_root / "tests" / Path(*parts)

            if test_path.exists():
                return test_path

    except (ValueError, IndexError):
        pass

    return None


def is_python_file(file_path: Path) -> bool:
    """Check if file is a Python file"""
    return file_path.suffix == '.py'


def is_test_file(file_path: Path) -> bool:
    """Check if file is a test file"""
    return file_path.name.startswith('test_') and file_path.suffix == '.py'


def is_source_file(file_path: Path, project_root: Path) -> bool:
    """Check if file is a source file in nf_core directory"""
    try:
        rel_path = file_path.relative_to(project_root)
        return (
            rel_path.parts
            and rel_path.parts[0] == "nf_core"
            and file_path.suffix == '.py'
        )
    except ValueError:
        return False


def run_tests_for_file(test_file: Path, project_root: Path) -> Tuple[bool, str]:
    """Run pytest for a specific test file"""
    cmd = ["uv", "run", "python", "-m", "pytest", str(test_file), "-v"]
    exit_code, stdout, stderr = run_command(cmd, project_root)

    if exit_code == 0:
        return True, f"✅ Tests passed for {test_file.name}"
    else:
        # Include both stdout and stderr in error message
        error_output = []
        if stderr:
            error_output.append(f"STDERR:\n{stderr}")
        if stdout:
            error_output.append(f"STDOUT:\n{stdout}")

        error_msg = f"❌ Tests failed for {test_file.name}\n" + "\n".join(error_output)
        return False, error_msg


def run_ruff_check(file_path: Path, project_root: Path) -> Tuple[bool, str]:
    """Run ruff linting on a file"""
    cmd = ["uv", "run", "ruff", "check", str(file_path)]
    exit_code, stdout, stderr = run_command(cmd, project_root)

    if exit_code == 0:
        return True, f"✅ Ruff linting passed for {file_path.name}"
    else:
        error_msg = f"❌ Ruff linting issues in {file_path.name}:\n{stdout}{stderr}"
        return False, error_msg


def run_ruff_format(file_path: Path, project_root: Path) -> Tuple[bool, str]:
    """Run ruff formatting on a file"""
    cmd = ["uv", "run", "ruff", "format", str(file_path), "--check"]
    exit_code, stdout, stderr = run_command(cmd, project_root)

    if exit_code == 0:
        return True, f"✅ Ruff formatting check passed for {file_path.name}"
    else:
        error_msg = f"❌ Ruff formatting issues in {file_path.name}:\n{stdout}{stderr}"
        return False, error_msg


def run_mypy_check(file_path: Path, project_root: Path) -> Tuple[bool, str]:
    """Run mypy type checking on a file"""
    cmd = ["uv", "run", "mypy", str(file_path)]
    exit_code, stdout, stderr = run_command(cmd, project_root)

    if exit_code == 0:
        return True, f"✅ MyPy type checking passed for {file_path.name}"
    else:
        # If single file check fails, try directory-level check
        if is_source_file(file_path, project_root):
            cmd_dir = ["uv", "run", "mypy", "nf_core/"]
            exit_code_dir, stdout_dir, stderr_dir = run_command(cmd_dir, project_root)

            if exit_code_dir == 0:
                return True, f"✅ MyPy type checking passed (directory-level) for {file_path.name}"
            else:
                error_msg = f"❌ MyPy type checking issues:\n{stdout_dir}{stderr_dir}"
                return False, error_msg
        else:
            error_msg = f"❌ MyPy type checking issues in {file_path.name}:\n{stdout}{stderr}"
            return False, error_msg


def process_edited_file(file_path: Path, project_root: Path) -> List[str]:
    """Process an edited file and return list of messages"""
    messages = []

    if not is_python_file(file_path):
        return [f"ℹ️ Skipping non-Python file: {file_path.name}"]

    # Handle test files
    if is_test_file(file_path):
        success, message = run_tests_for_file(file_path, project_root)
        messages.append(message)

        # Also run linting on test files
        success, message = run_ruff_check(file_path, project_root)
        messages.append(message)

        return messages

    # Handle source files
    if is_source_file(file_path, project_root):
        # Run related tests if they exist
        test_file = find_related_test_file(file_path, project_root)
        if test_file:
            success, message = run_tests_for_file(test_file, project_root)
            messages.append(message)

        # Run linting and type checking
        success, message = run_ruff_check(file_path, project_root)
        messages.append(message)

        success, message = run_ruff_format(file_path, project_root)
        messages.append(message)

        success, message = run_mypy_check(file_path, project_root)
        messages.append(message)

        return messages

    # Handle other Python files (run basic linting)
    if is_python_file(file_path):
        success, message = run_ruff_check(file_path, project_root)
        messages.append(message)
        return messages

    return [f"ℹ️ No specific actions for file: {file_path.name}"]


def main():
    """Main hook execution"""
    try:
        # Parse input from Claude Code
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract file path from tool input
    tool_input = input_data.get("tool_input", {})
    file_path_str = tool_input.get("file_path")

    if not file_path_str:
        # No file path, nothing to do
        sys.exit(0)

    file_path = Path(file_path_str)

    # Get project root from environment variable
    project_root_str = input_data.get("cwd")
    if not project_root_str:
        print("Error: No current working directory provided", file=sys.stderr)
        sys.exit(1)

    project_root = Path(project_root_str)

    # Process the edited file
    messages = process_edited_file(file_path, project_root)

    # Output results
    for message in messages:
        print(message)

    # Check if any errors occurred
    has_errors = any("❌" in msg for msg in messages)

    if has_errors:
        # Use exit code 2 to show errors to Claude
        sys.exit(2)
    else:
        # Success
        sys.exit(0)


if __name__ == "__main__":
    main()