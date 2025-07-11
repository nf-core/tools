# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The `nf-core/tools` repository contains a comprehensive Python package that provides command-line tools for the nf-core community. This package helps users run, create, and develop nf-core Nextflow pipelines with integrated support for modules, subworkflows, and schema management.

## Development Commands

### Testing

```bash
# Run all tests with pytest
python -m pytest

# Run specific test file
python -m pytest tests/test_<module>.py

# Run tests with coverage
python -m pytest --cov --cov-config=.coveragerc

# Run with verbose output
python -m pytest -v

# Run tests with specific markers
python -m pytest -m "datafiles"
```

### Code Quality and Linting

```bash
# Run pre-commit hooks (includes ruff formatting and linting)
pre-commit run --all-files

# Run ruff linter
ruff check .

# Run ruff formatter
ruff format .

# Run mypy type checking
mypy nf_core/
```

### Development Setup

```bash
# Install in development mode with dev dependencies
pip install --upgrade -r requirements-dev.txt -e .

# Install pre-commit hooks
pre-commit install

# Build package
python -m build

# Install package locally
pip install -e .
```

## Architecture Overview

### Core Structure

The codebase is organized into several key domains:

**Command Structure**: The main CLI interface is defined in `nf_core/__main__.py` using Click with rich-click for enhanced formatting. Commands are organized hierarchically:

- `pipelines/` - Pipeline management (create, lint, download, sync, etc.)
- `modules/` - Module management (install, update, create, test, etc.)
- `subworkflows/` - Subworkflow management (similar to modules)
- `test_datasets/` - Test dataset management

**Component Architecture**:

- `nf_core/components/` - Shared functionality for modules and subworkflows
- `nf_core/pipelines/` - Pipeline-specific operations including lint tests
- `nf_core/modules/` - Module-specific operations and lint tests
- `nf_core/subworkflows/` - Subworkflow-specific operations

### Key Design Patterns

**Lint System**: Both pipelines and modules use a comprehensive lint system:

- `nf_core/pipelines/lint/` - Contains individual lint test files
- `nf_core/modules/lint/` - Module-specific lint tests
- Each lint test is a separate Python module with standardized interface

**Template System**: Templates are stored in dedicated directories:

- `nf_core/pipeline-template/` - Complete pipeline template with Jinja2 templating
- `nf_core/module-template/` - Module template for creating new modules
- `nf_core/subworkflow-template/` - Subworkflow template

**Component Management**: Modules and subworkflows share common patterns:

- JSON tracking files (`modules.json`) for version management
- Git-based remote repository integration
- Local vs remote component distinction
- Patch system for local modifications

### Data Flow

1. **Command Parsing**: Click commands in `__main__.py` parse arguments and delegate to command modules
2. **Context Management**: Click context objects carry configuration and state between commands
3. **Git Operations**: Remote repository operations for fetching modules/subworkflows
4. **Template Processing**: Jinja2 templating for generating new pipelines/modules
5. **Lint Execution**: Modular lint system with individual test execution and reporting

## Testing Strategy

### Test Organization

- Tests mirror the source structure under `tests/`
- Integration tests use real pipeline/module examples
- Snapshot testing for CLI output with pytest-textual-snapshot
- Workflow testing with pytest-workflow for pipeline execution

### Test Data

- `tests/data/` - Mock configurations and test data
- `tests/fixtures/` - Reusable test fixtures
- Pipeline templates and module examples for integration testing

### Key Testing Patterns

- Use `@pytest.mark.datafiles` for tests requiring file fixtures
- Snapshot tests for CLI output verification
- Mock external dependencies (GitHub API, Docker registry)
- Parameterized tests for multiple scenarios

## Important Implementation Details

### Configuration Management

- Global configuration in `~/.nfcore/` directory
- Rich console output with color support
- Environment variable support with `NFCORE_` prefix
- Logging configuration with file and console handlers

### Error Handling

- Custom exception hierarchy for different error types
- Selective traceback display for user-friendly error messages
- Graceful degradation for network failures

### Performance Considerations

- Parallel processing for download operations
- Caching for remote repository operations
- Progress bars for long-running operations
- Lazy loading of large data structures

## Development Notes

### Adding New Commands

1. Add command function to appropriate `commands_*.py` file
2. Add Click decorator and options in `__main__.py`
3. Update command groups in `COMMAND_GROUPS` dictionary
4. Add comprehensive tests in `tests/` directory
5. Update documentation if needed

### Lint Test Development

1. Create new lint test module in appropriate `lint/` directory
2. Implement test class with `run()` method
3. Add test to main lint runner
4. Create comprehensive test cases
5. Update documentation with test description

### Template Updates

1. Modify template files in respective `-template/` directories
2. Test template generation with various options
3. Update template tests and snapshots
4. Consider backward compatibility for existing pipelines

This codebase emphasizes modularity, comprehensive testing, and user experience through rich CLI interfaces and detailed error reporting.
