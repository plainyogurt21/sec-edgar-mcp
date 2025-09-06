FROM python:3.13-slim

# Install server dependencies
RUN pip install --no-cache-dir \
    "mcp[cli]>=1.7.1" \
    "edgartools" \
    "packaging" \
    "requests" \
    "python-dotenv" \
    "fastapi>=0.110" \
    "uvicorn[standard]>=0.23"

# Copy source
WORKDIR /app
COPY . .

# Ensure local package is discoverable
ENV PYTHONPATH=/app

# Default to HTTP transport when running in a container; stdio remains available locally
ENV TRANSPORT=http
ENV PORT=8081

EXPOSE 8081

# The server requires NASDAQ_DATA_LINK_API_KEY to be set at runtime
# Example mcpServers config for your client:
# 
# "mcpServers": {
#   "sec-edgar-mcp": {
#     "command": "docker",
#     "args": [
#       "run",
#       "--rm",
#       "-i",
#       "-e", "SEC_EDGAR_USER_AGENT=<First Name, Last name (your@email.com)>",
#       "stefanoamorelli/nasdaq-data-link-mcp:latest"
#     ]
#   }
# }

CMD ["python", "sec_edgar_mcp/server.py"]
