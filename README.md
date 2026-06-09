# University Academic Management System

A CLI-based academic management system built with Python, demonstrating
professional project structure, type safety, and testing practices.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) *(recommended)* or plain pip + venv

---

## Setup

### Option A — uv (recommended, modern)

```bash
# Install uv if you don't have it (Windows PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create .venv, install package + dev deps in one step
cd university-system
uv sync --dev

# Run the app
uv run python main.py
```

### Option B — plain venv + pip

```bash
cd university-system
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install package in editable mode + dev tools
pip install -e ".[dev]"

# Run the app
python main.py
```

---

## Development commands

```bash
# Run tests
pytest

# Run tests with coverage report
pytest --cov=university --cov-report=term-missing

# Static type checking
mypy src/

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

With uv, prefix each command with `uv run`:

```bash
uv run pytest --cov=university --cov-report=term-missing
uv run mypy src/
uv run ruff check src/ tests/
```

---

## Configuration

All settings have sensible defaults and can be overridden via environment variables.
Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `UNIVERSITY_DATA_PATH` | `./data/university_data.json` | JSON data file location |
| `UNIVERSITY_MAX_CREDITS` | `18` | Max credits per semester |
| `UNIVERSITY_PROBATION_THRESHOLD` | `2.0` | GPA below which → Probation |
| `UNIVERSITY_DISMISSAL_THRESHOLD` | `1.0` | GPA below which (×2) → Dismissed |
| `UNIVERSITY_DEANS_LIST_GPA` | `3.7` | Min GPA for Dean's List |
| `UNIVERSITY_DEANS_LIST_CREDITS` | `12` | Min credits for Dean's List |
| `UNIVERSITY_LOG_PATH` | `./university.log` | Log file location |

---

## Project structure

```
university-system/
├── src/
│   └── university/
│       ├── __init__.py          # Package marker + version
│       ├── py.typed             # PEP 561 — declares typed package
│       ├── config.py            # Centralised settings (env var driven)
│       ├── exceptions.py        # Custom exception hierarchy
│       ├── manager.py           # Business logic orchestration
│       ├── persistence.py       # JSON save/load (swap for DB here)
│       ├── cli.py               # Interactive menu (I/O only)
│       └── models/
│           ├── __init__.py
│           ├── person.py        # Abstract base class
│           ├── student.py       # Student model + GPA logic
│           └── course.py        # Course model + analytics
├── tests/
│   ├── conftest.py              # Shared pytest fixtures
│   ├── test_student.py          # Student unit tests
│   ├── test_course.py           # Course unit tests
│   └── test_manager.py          # Integration tests
├── data/
│   └── .gitkeep                 # Dir committed, data files gitignored
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions: lint → type → test
├── .env.example                 # Documents all env vars
├── .gitignore
├── CHANGELOG.md
├── pyproject.toml               # Project config, tooling, deps
├── main.py                      # 5-line entry point
└── README.md
```

---

## Design decisions

**src layout** — all code under `src/university/` prevents accidental
import of the local folder instead of the installed package.

**Separation of concerns** — models know nothing about each other.
`UniversityManager` is the only place that wires `Student` and `Course` together.
`persistence.py` is pure I/O — swapping to a database only touches that file.

**Type annotations + mypy strict** — every function is fully annotated.
`mypy --strict` runs in CI, catching type errors before they reach runtime.

**Config over hardcoding** — all tunable values live in `config.py` and
are overridable via environment variables. No magic numbers in business logic.

**conftest.py** — shared test fixtures defined once, used across all
test modules. No duplication.
