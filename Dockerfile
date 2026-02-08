FROM ghcr.io/astral-sh/uv:python3.13-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=".:$PYTHONPATH"
ENV TZ=Asia/Tokyo
ENV PORT=8080

# Install Node.js 24
RUN apt-get update && apt-get install -y curl gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock LICENSE ./

RUN uv sync --frozen --no-cache

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY skills/ ./skills/

EXPOSE ${PORT:-8080}

ENTRYPOINT ["sh", "-c", "uv run agent-skills-mcp --transport http --host 0.0.0.0 --port ${PORT:-8080}"]
