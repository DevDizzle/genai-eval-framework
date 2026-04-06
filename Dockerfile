FROM python:3.11-slim-bookworm

# Install uv
RUN pip install uv

# Create app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Copy application code (needed for editable install with setuptools)
COPY src /app/src
COPY configs /app/configs

# Install dependencies using uv
RUN uv pip install --system -e .

# Expose port for Cloud Run
EXPOSE 8080

# Run FastAPI app
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]
