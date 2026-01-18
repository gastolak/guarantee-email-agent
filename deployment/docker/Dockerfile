FROM python:3.10-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY instructions/ ./instructions/
COPY config.yaml ./

# Install dependencies
RUN uv sync --frozen

# Copy entrypoint
COPY deployment/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs

# Run as non-root user
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /app
USER agent

# Use entrypoint for signal handling
ENTRYPOINT ["/entrypoint.sh"]
