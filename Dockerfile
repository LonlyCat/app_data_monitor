FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Ensure entrypoint is executable (in case git perms were lost)
USER root
RUN chmod +x /app/docker/entrypoint.sh && chown appuser:appuser /app/docker/entrypoint.sh
USER appuser

# Entrypoint handles migrations/static, then execs the given command
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Default command runs gunicorn; compose can override with runserver for dev
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app_monitor.wsgi:application"]
