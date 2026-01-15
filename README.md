# ccdemo

A Python demo project.

## Development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Lint and format
ruff check .
ruff format .
```

## Project Structure

```
ccdemo/
├── src/           # Source code
├── tests/         # Tests
├── scripts/       # Utility scripts
└── pyproject.toml # Project configuration
```
