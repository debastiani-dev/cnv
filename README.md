# Cabanha Nelore do Vale (CNV) System

This project is the backend containing all business rules for the CNV platform, available via Django templates and API.
The project is developed with [Django](https://docs.djangoproject.com/) and uses [TailwindCSS](https://tailwindcss.com/) for styling.

## Table of Contents

- [Cabanha Nelore do Vale (CNV) System](#cabanha-nelore-do-vale-cnv-system)
- [Table of Contents](#table-of-contents)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
  - [Development Environment](#development-environment)
  - [Access and Documentation](#access-and-documentation)
- [Development](#development)
  - [Basic Commands](#basic-commands)
  - [Frontend (TailwindCSS)](#frontend-tailwindcss)
- [Project Structure](#project-structure)
  - [Apps Organization](#apps-organization)
  - [Test Structure](#test-structure)
- [Tests](#tests)
  - [Execution](#execution)
  - [Best Practices](#best-practices)
- [Deployment](#deployment)
  - [Environments](#environments)
  - [Deployment Process](#deployment-process)
- [Code Standards](#code-standards)
  - [Formatting](#formatting)
  - [Pre-commit Hooks](#pre-commit-hooks)

## Prerequisites

- [Python](https://www.python.org/downloads/) 3.12+
- [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Node.js](https://nodejs.org/) (for TailwindCSS)

## Configuration

### Development Environment

1. Clone the repository:
```bash
git clone [repo-url]
cd cnv
```

2. Install Python dependencies:
```bash
poetry install
```

3. Install Node dependencies (for CSS):
```bash
npm install
```

4. Start the environment:
```bash
# Use make to start containers (DB, etc.) and run the server
make dev/up
```

### Access and Documentation

- Application: http://localhost:8000/
- Admin: http://localhost:8000/admin/

## Development

### Basic Commands
```bash
# Start environment
make dev/up

# Stop containers
make dev/down

# View logs
make dev/logs

# Access Django shell
make dev/shell
```

### Frontend (TailwindCSS)
The project uses TailwindCSS. For frontend development:

```bash
# Watch for CSS changes (Watch mode)
make css-watch

# Build CSS for production
make css-build
```

## Project Structure

### Apps Organization
```
apps/
  ├── base/           # Base functionalities and layouts
  ├── authentication/ # Authentication and Custom Users
  ├── cattle/         # Cattle Management (Nelore)
  ├── dashboard/      # Administrative Dashboard
  └── website/        # Public Landing Page

Each app follows the standard Django structure:
  ├── models/        # Models
  ├── views/         # Views
  ├── templates/     # HTML Templates
  ├── services/      # Business Logic (Service Layer)
  ├── admin/         # Admin configurations
  └── forms.py       # Forms
```

### Test Structure
The test structure follows the Django/Pytest pattern:
```
tests/
  ├── conftest.py         # Shared fixtures
  ├── authentication/     # Authentication tests
  ├── cattle/             # Cattle tests
  └── ...
```

## Tests

The project uses [pytest](https://docs.pytest.org/) as the test framework:

- Shared fixtures in `conftest.py`
- Factories using [model-bakery](https://model-bakery.readthedocs.io/)

### Execution
```bash
# All tests
make pytest

# With coverage report
make pytest-cov

# Specific tests
make pytest opts="-k test_name"
```

### Best Practices
- Use fixtures instead of setup methods
- Prefer `pytest.mark.parametrize` for similar test cases
- Keep tests focused and with descriptive names

## Deployment

### Environments
The project has two deployment environments defined in the Makefile:
- `hom` = Staging (Homologation)
- `prd` = Production

### Deployment Process
Deployments are performed via Git tags:

```bash
# Release scripts available:
make release-hom
make release-prd
```

## Code Standards

The project follows rigorous code standards verified via CI:

- [Black](https://black.readthedocs.io/): Python code formatter
- [isort](https://pycqa.github.io/isort/): Import sorting
- [Flake8](https://flake8.pycqa.org/): PEP 8 style verification
- [MyPy](https://mypy.readthedocs.io/): Type hint verification
- [Pylint](https://pylint.readthedocs.io/): Static analysis
- [Pre-commit](https://pre-commit.com/): Git hooks

### Formatting
```bash
# Format code (autoflake8, isort, black)
make format

# Check style (full linting)
make lint
```

### Pre-commit Hooks
Use [pre-commit](https://pre-commit.com/) to ensure code quality before every commit:
```bash
pre-commit install --install-hooks
```
