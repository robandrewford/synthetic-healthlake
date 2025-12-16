FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dbt project
COPY dbt/fhir_omop_dbt/ ./dbt/fhir_omop_dbt/
COPY pyproject.toml ./

# Install dbt and dependencies
RUN uv pip install --system dbt-duckdb>=1.5.0 dbt-athena-community>=1.7.0

# Install AWS CLI
RUN uv pip install --system awscli

# Set working directory to dbt project
WORKDIR /app/dbt/fhir_omop_dbt

CMD ["/bin/bash"]
