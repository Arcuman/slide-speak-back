# Dockerfile
FROM --platform=$TARGETPLATFORM python:3.10-slim

# Set ARG for platform detection
ARG TARGETPLATFORM

# 1) Install build deps + tini
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/* \
 # Install appropriate tini version based on architecture
 && if [ "$(uname -m)" = "aarch64" ]; then \
      curl -sLo /usr/bin/tini https://github.com/krallin/tini/releases/download/v0.19.0/tini-arm64; \
    else \
      curl -sLo /usr/bin/tini https://github.com/krallin/tini/releases/download/v0.19.0/tini-amd64; \
    fi \
 && chmod +x /usr/bin/tini

WORKDIR /app

# 2) Copy and install python deps
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 3) Copy all code
COPY . .

# 4) Expose both ports
EXPOSE ${PORT}             
EXPOSE ${INDEX_SERVER_PORT}

# 5) Use tini to forward signals; no default CMD so each service can pick its own
ENTRYPOINT ["/usr/bin/tini", "--"]
