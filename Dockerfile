FROM ghcr.io/astral-sh/uv:python3.13-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=".:$PYTHONPATH"
ENV TZ=Asia/Tokyo
ENV PORT=8080

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY skills/ ./skills/

EXPOSE ${PORT:-8080}

ENTRYPOINT ["sh", "-c", "uv run agent-skills-mcp --transport http --host 0.0.0.0 --port ${PORT:-8080}"]
