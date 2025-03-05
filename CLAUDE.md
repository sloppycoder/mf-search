# MF-Search Project Guidelines

## Build & Test Commands
- Setup: `uv sync && source .venv/bin/activate`
- Run app: `python main.py` (append `-f` to force overwrite)
- Lint: `ruff check --fix .`
- Format: `ruff format .`
- Type check: `pyright`
- Run all tests: `pytest -s tests/`
- Run single test: `pytest -s tests/test_mutual_fund_search.py::test_mutual_fund_search`

## Code Style Guidelines
- Line length: 90 characters max
- Indentation: 4 spaces
- Use Python 3.12+ features and type hints
- Import order: standard library, third-party, local (enforced by ruff)
- Error handling: Use try/except blocks with specific exceptions
- Naming: snake_case for functions/variables, PascalCase for classes
- Use string literals for type annotations in Python 3.12+
- Pre-commit hooks must pass before commits (pyright, ruff check/format)
- Document functions with docstrings, especially complex functions
- Use pathlib for file paths, not os.path
