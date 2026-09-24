FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY . .

RUN uv sync --locked --python 3.12 --package lokara-api --no-dev --no-editable \
    && rm -rf /root/.cache/uv

USER pwuser

EXPOSE 10000

CMD ["sh", "-c", "exec uvicorn lokara_api.main:app --host 0.0.0.0 --port \"${PORT:-10000}\""]
