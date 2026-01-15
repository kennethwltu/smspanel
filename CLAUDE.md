# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

Standard Python package layout:

- `src/` - Main source code (installable package)
- `tests/` - Pytest tests (mirrors `src/ structure`)
- `scripts/` - Utility and maintenance scripts
- `pyproject.toml` - Project configuration, pytest settings, ruff config

## Commands

### Development Setup

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Running Tests

```bash
# All tests
pytest

# Single test file
pytest tests/test_example.py

# Specific test
pytest tests/test_example.py::test_function_name

# With coverage
pytest --cov=src --cov-report=term-missing
```

### Code Quality

```bash
# Lint
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format
ruff format .
```

### Installation

Install in editable mode for development:

```bash
pip install -e .
```
