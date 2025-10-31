# Multi-stage build for TopoKit
FROM node:20-alpine AS node-builder

# Install pnpm
RUN npm install -g pnpm@8

# Build TypeScript CLI
WORKDIR /app/packages/cli
COPY packages/cli/package.json packages/cli/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY packages/cli/ ./
RUN pnpm run build

# Python runtime stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and pnpm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm@8

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY packages/core/pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy built CLI from node-builder stage
COPY --from=node-builder /app/packages/cli/dist ./packages/cli/dist
COPY --from=node-builder /app/packages/cli/package.json ./packages/cli/
COPY --from=node-builder /app/packages/cli/node_modules ./packages/cli/node_modules

# Create symlink for CLI
RUN ln -s /app/packages/cli/dist/index.js /usr/local/bin/topokit-cli

# Copy sample topology
COPY topology/ ./topology/

# Create non-root user
RUN useradd -m -u 1000 topokit && \
    chown -R topokit:topokit /app
USER topokit

# Expose port for monitoring
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD topokit-cli --version || exit 1

# Default command
CMD ["topokit-cli", "--help"]
