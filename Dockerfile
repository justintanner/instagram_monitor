FROM python:3.12-slim

LABEL maintainer="instagram_monitor"
LABEL description="Instagram monitoring OSINT tool"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 monitor

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY start.py .
COPY src/ ./src/
COPY assets/ ./assets/
COPY .env.example .

# Create data directory for persistent storage
RUN mkdir -p /app/data/logs /app/data/images && chown -R monitor:monitor /app

# Switch to non-root user
USER monitor

# Data volume for logs, session files, and downloaded media
VOLUME ["/app/data"]

# Default entrypoint
ENTRYPOINT ["python", "start.py"]

# Default command (show help)
CMD ["--help"]
