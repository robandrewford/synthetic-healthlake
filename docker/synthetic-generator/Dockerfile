FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy project files
COPY pyproject.toml ./
COPY synthetic/ ./synthetic/

# Install Python dependencies
RUN uv pip install --system -e .

# Install AWS CLI for S3 uploads
RUN uv pip install --system awscli

# Make scripts executable
RUN chmod +x /app/scripts/*.sh || true

CMD ["/bin/bash"]
