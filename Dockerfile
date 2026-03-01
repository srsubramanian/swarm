# Stage 1: Build frontend (full ubi9 for dnf module support — Node 20)
FROM registry.access.redhat.com/ubi9/ubi:latest AS frontend-build

RUN dnf module enable -y nodejs:20 && \
    dnf install -y nodejs npm && \
    dnf clean all

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# Stage 2: Runtime — nginx + uvicorn + supervisord
FROM registry.access.redhat.com/ubi9/ubi-minimal:latest

RUN microdnf install -y python3.11 python3.11-pip nginx && \
    microdnf clean all && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    pip3.11 install --no-cache-dir supervisor

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Backend dependencies
WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app/ app/

# Frontend static files
COPY --from=frontend-build /build/dist /usr/share/nginx/html

# Config files
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 3000

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
