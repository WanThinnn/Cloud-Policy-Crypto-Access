# Build Tailwind assets separately to keep runtime image slim
FROM node:20-alpine AS tailwind-builder
WORKDIR /app

# Copy the entire source code so Tailwind can scan templates
COPY src/ ./src/

WORKDIR /app/src/theme/static_src
RUN npm ci
RUN npm run build

# Final runtime image
FROM ubuntu:24.04

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    python3-venv \
    gcc \
    sqlite3 \
    libglib2.0-0 \
    libgmp10 \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

COPY src/ /app/
COPY --from=tailwind-builder /app/src/theme/static/css/dist /app/theme/static/css/dist

RUN mkdir -p /app/data /app/staticfiles /app/logs

RUN DJANGO_SECRET_KEY=dummy DJANGO_ALLOWED_HOSTS=* DATABASE_URL=postgres://dummy:dummy@localhost:5432/dummy python manage.py collectstatic --noinput || true

RUN chmod -R 755 /app && \
    chmod -R 777 /app/data /app/logs

EXPOSE 8000

CMD python manage.py migrate --noinput && \
    python manage.py init_settings && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
