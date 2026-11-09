# One image for the live demo: the built frontend and the API on one port, with the v0 model inside.
# .github/workflows/image.yml builds it, tests it and publishes it. Nothing here runs on a laptop.
# The workflow puts the model in model/clauseanchor_candidate_v0 before the build. The weights are never in git.

# Stage 1: the frontend, from its lockfile. pnpm 10.34.3 and Node 22 are what the repo was built with.
FROM node:22-slim AS web
RUN npm install --global pnpm@10.34.3
WORKDIR /web
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
# check:dist fails the build if dist holds a mock adapter or sample contract text (Architecture.md 7.1)
RUN pnpm build && pnpm check:dist

# Stage 2: the API, the core and the model on Python 3.12.
FROM python:3.12-slim
# Links the package on GitHub to this repository, so the workflow's token may push to it
LABEL org.opencontainers.image.source="https://github.com/TheMEGALODON55681/clauseanchor"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# CPU torch first, from the official CPU index, so the pin in requirements-inference.txt is already met
# and no CUDA build is fetched (docs/ml/ReleaseHandoff.md section 3)
COPY ml/requirements-inference.txt ml/requirements-inference.txt
RUN pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r ml/requirements-inference.txt

# requirements.txt ends in an editable install of ../ml. The core goes in below as a normal install.
COPY backend/requirements.txt backend/constraints.txt backend/
RUN grep -v '^-e ' backend/requirements.txt > /tmp/requirements.txt \
 && pip install -r /tmp/requirements.txt -c backend/constraints.txt \
 && rm /tmp/requirements.txt

# The API reads ml/configs/catalogue.json in place, found from backend/app/config.py, so ml/ stays
# at the same place relative to backend/
COPY ml/ ml/
RUN pip install ./ml

COPY model/clauseanchor_candidate_v0 model/clauseanchor_candidate_v0
COPY backend/app backend/app
COPY --from=web /web/dist frontend-dist
COPY LICENSE LICENSE

# The model and the analyzer's own switches. 2 matches the 2 vCPU the app runs on: torch counts the
# host's cores and not the container's quota, so it would start too many threads. Change both if the vCPU count changes.
ENV CLAUSEANCHOR_ANALYZER=real \
    CLAUSEANCHOR_ARTIFACTS_DIR=/app/model/clauseanchor_candidate_v0 \
    CLAUSEANCHOR_ARTIFACTS_SHA256=ccf0c0b6e216685955e433cb6194ba2e40ccc85801b016a2a7fa026ef0ae57e8 \
    CLAUSEANCHOR_DB_PATH=:memory: \
    CLAUSEANCHOR_FRONTEND_DIST=/app/frontend-dist \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    MALLOC_ARENA_MAX=2 \
    HF_HUB_OFFLINE=1

# The API and its parse children run as a user that owns nothing under /app. It has a home folder,
# so a library that wants a cache folder does not fail on a missing one.
RUN useradd --system --create-home --shell /usr/sbin/nologin app
USER app

WORKDIR /app/backend
EXPOSE 8000
# Liveness only: /health checks no dependency, so it answers while the model loads
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"]
# No core dumps (R15): a dump would hold every stored contract. One worker, because sessions live in this process.
CMD ["sh", "-c", "ulimit -c 0 && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --workers 1 --no-server-header"]
