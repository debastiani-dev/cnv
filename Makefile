SHELL := /bin/bash -o pipefail

ifndef NOCOLOR
	RED    := $(shell tput -Txterm setaf 1)
	GREEN  := $(shell tput -Txterm setaf 2)
	YELLOW := $(shell tput -Txterm setaf 3)
	RESET  := $(shell tput -Txterm sgr0)
endif

ifdef CI
	V ?= 1
endif

ifeq ("$(dir ${GITHUB_REF})", "refs/tags/")
  SOURCE_TAG=$(notdir ${GITHUB_REF})
endif

ifdef GITHUB_SHA
  SOURCE_TAG ?= ${GITHUB_SHA}
endif

PYTHON_FILES := $(shell find . -type f -name "*.py" ! -path "*/\.*" ! -path "*/migrations/*" ! -path "*/venv/*" ! -path "*/env/*")
ifdef subdirectory
PYTHON_FILES := $(shell find $(subdirectory) -type f -name "*.py" ! -path "*/\.*" ! -path "*/migrations/*" ! -path "*/venv/*" ! -path "*/env/*")
endif

## Help for all Targets
.PHONY: help
help:
	@awk '/^.PHONY: / { \
		msg = match(lastLine, /^## /); \
			if (msg) { \
				cmd = substr($$0, 9, 100); \
				msg = substr(lastLine, 4, 1000); \
				printf "  ${GREEN}%-30s${RESET} %s\n", cmd, msg; \
			} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

## Verifies dependencies of the project
.PHONY: deps-check
deps-check:
	@echo "${GREEN}Verifying dependencies${RESET}"
	poetry check --lock || exit 1
	poetry check || exit 1

## Starts development environment
.PHONY: dev/up
dev/up: deps-check
	@echo "${GREEN}Starting development environment${RESET}"
	teller run -- docker compose --env-file .env up

## Stops and removes running containers
.PHONY: dev/down
dev/down:
	@echo "${GREEN}Stopping containers${RESET}"
	docker compose down

## Accesses the web container shell
.PHONY: dev/shell
dev/shell:
	@echo "${GREEN}Accessing web container shell${RESET}"
	docker compose exec web bash

## Tracks container logs
.PHONY: dev/logs
dev/logs:
	@echo "${GREEN}Tracking container logs${RESET}"
	docker compose logs -f

## Make migrations
.PHONY: dev/makemigrations
dev/makemigrations:
	@echo "${GREEN}Making migrations${RESET}"
	docker compose exec web python manage.py makemigrations

## Apply migrations
.PHONY: dev/migrate
dev/migrate:
	@echo "${GREEN}Applying migrations${RESET}"
	docker compose exec web python manage.py migrate

## Checks code with isort
.PHONY: lint-isort
lint-isort:
	@echo "Linting isort..."
	-@poetry run isort --profile='black' --check-only --diff $(PYTHON_FILES)

## Checks code with black
.PHONY: lint-black
lint-black:
	@echo "Linting black..."
	-@poetry run black --check --preview $(PYTHON_FILES)

## Checks code with flake8
.PHONY: lint-flake8
lint-flake8:
	@echo "Linting flake8..."
	-@poetry run flake8 --statistics --exit-zero $(PYTHON_FILES)

## Checks code with mypy
.PHONY: lint-mypy
lint-mypy:
	@echo "Linting mypy..."
	-@poetry run mypy $(PYTHON_FILES)

## Checks code with pylint
.PHONY: lint-pylint
lint-pylint:
	@echo "Linting pylint..."
	-@poetry run pylint --rcfile=.pylintrc $(PYTHON_FILES) 

## Checks code with all linters of the project
.PHONY: lint
lint: lint-isort lint-black lint-flake8 lint-mypy lint-pylint

## Formats code with isort
.PHONY: format-isort
format-isort:
	@echo "Running isort..."
	poetry run isort --profile='black' $(PYTHON_FILES)

## Formats code with black
.PHONY: format-black
format-black:
	@echo "Running black..."
	poetry run black --preview -v $(PYTHON_FILES)

## Formats code with autoflake8
.PHONY: format-autoflake8
format-autoflake8:
	@echo "Running autoflake8..."
	poetry run autoflake8 --in-place -vv $(PYTHON_FILES)

## Formats code with formatters of the project
.PHONY: format
format: format-autoflake8 format-isort format-black

## Runs pre-commit hooks
.PHONY: run-pre-commit-hook
run-pre-commit-hook:
	bash .git/hooks/pre-commit

## Runs all tests of the project (use: make pytest opts="-k nome_do_teste" for specific tests)
.PHONY: pytest
pytest:
	@echo "${GREEN}Running tests with pytest${RESET}"
	docker compose \
	-f docker-compose.test.yml \
	run --rm web python -m pytest -v --tb=short --reuse-db --cache-clear $(opts)

## Runs tests with coverage report
.PHONY: pytest-cov
pytest-cov:
	@echo "${GREEN}Running tests with coverage report${RESET}"
	python -m pytest --cov=apps --cov-report=term-missing -v --tb=short --reuse-db --cache-clear $(opts)
