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

# Install runtime deps from requirements.txt (aligns with pyproject)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Now copy the source
COPY . .

ENV PYTHONPATH=/app \
    TRANSPORT=http \
    PORT=8081

EXPOSE 8081

# IMPORTANT: run as a module so relative imports work
CMD ["python", "-m", "sec_edgar_mcp.server"]
