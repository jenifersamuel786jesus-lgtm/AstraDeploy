FROM node:22-slim AS frontend-build
WORKDIR /workspace
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.json vite.config.ts ./
COPY frontend ./frontend
COPY backend ./backend
RUN pnpm install --frozen-lockfile
RUN pnpm build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt alembic.ini ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY public ./public
COPY --from=frontend-build /workspace/backend/app/static ./backend/app/static
EXPOSE 3000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
