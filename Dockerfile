FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false


# 1. Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl gnupg gettext locales \
    && sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && mkdir -p /etc/apt/keyrings \
    # ... (Keep Node.js installation lines 16-24) ...
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version 2.0.0
ENV PATH="/root/.local/bin:$POETRY_HOME/bin:$PATH"

WORKDIR /app

# 3. Install Python Dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# 4. Install Node Dependencies & Build Tailwind
COPY package.json ./
RUN npm install

# Copy project files
COPY . .

# Build CSS
RUN npm run build

# Collect Static Files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Default command
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]