FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Faster, cleaner builds
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy only metadata first for better layer caching (if present)
COPY pyproject.toml ./
# If you have a lock file, copy it too:
# COPY uv.lock ./

# Install runtime deps. Prefer installing your package so its deps come in too.
# If your project has a proper pyproject.toml, this will pull everything:
#   pip install .
# If not, fall back to explicit libs you need:
RUN pip install --no-cache-dir "mcp>=1.0.0" "edgartools" "requests" "python-dotenv" "packaging"

# Now copy the source
COPY . .

# Make local package discoverable
ENV PYTHONPATH=/app

# IMPORTANT: run as a module so relative imports work
CMD ["python", "-m", "sec_edgar_mcp.server"]
