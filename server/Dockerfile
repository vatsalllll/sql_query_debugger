FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the sql_debugger package
COPY . ./sql_debugger/

# Install dependencies
RUN pip install --no-cache-dir "openenv-core[core]>=0.2.2" wsproto && \
    pip install --no-cache-dir ./sql_debugger/

ENV PYTHONUNBUFFERED=1
ENV ENABLE_WEB_INTERFACE=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "sql_debugger.server.app:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "wsproto"]
