FROM python:3.12-alpine

WORKDIR /app

# Copy only pyproject.toml first for better layer caching
COPY pyproject.toml ./

# Install dependencies
RUN python -m pip install --no-cache-dir .

# Copy application code
COPY src /app/src
COPY locales /app/locales

# Create data directory and set volume
RUN mkdir -p /app/data
VOLUME ["/app/data"]

# Run as non-root user for security
ENV UID=1000
ENV GID=1000
RUN addgroup -g $UID appgroup && \
    adduser -u $GID -G appgroup -D appuser && \
    chown -R appuser:appgroup /app
USER appuser

ENTRYPOINT ["python", "-m", "src.client.telegram.main"]
