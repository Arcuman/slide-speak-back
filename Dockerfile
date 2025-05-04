FROM --platform=$TARGETPLATFORM python:3.10-slim

# install poppler-utils (for pdf2image) + build deps + tini
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential curl \
      poppler-utils \
 && rm -rf /var/lib/apt/lists/* \
 # install tini as before
 && if [ "$(uname -m)" = "aarch64" ]; then \
      curl -sLo /usr/bin/tini https://github.com/krallin/tini/releases/download/v0.19.0/tini-arm64; \
    else \
      curl -sLo /usr/bin/tini https://github.com/krallin/tini/releases/download/v0.19.0/tini-amd64; \
    fi \
 && chmod +x /usr/bin/tini

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${PORT}             
EXPOSE ${INDEX_SERVER_PORT}

ENTRYPOINT ["/usr/bin/tini", "--"]
