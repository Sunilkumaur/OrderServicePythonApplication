# ---------- Stage 1: install dependencies ----------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
# Install packages into an isolated folder we can copy into the final image
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: small runtime image ----------
FROM python:3.12-slim

# Don't write .pyc files; print logs immediately (important for container logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=local \
    APP_VERSION=dev

# Run as a non-root user (security best practice)
RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/

USER app
EXPOSE 8080

# Start the web server on port 8080, listening on all interfaces
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
