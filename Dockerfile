FROM rust:1-slim AS mkaos-rust-build
WORKDIR /src/engine/mkaos-inference
COPY engine/mkaos-inference/ ./
RUN cargo build --release --bin mkaos-generate

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-voice.txt requirements-media.txt ./
# Keep the default image lightweight. Optional local voice/STT and image-background
# packages are only installed when explicitly requested at build time.
ARG INSTALL_OPTIONAL_VOICE=false
ARG INSTALL_OPTIONAL_MEDIA=false
RUN if [ "$INSTALL_OPTIONAL_VOICE" = "true" ]; then \
      pip install --no-cache-dir -r requirements-voice.txt; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi && \
    if [ "$INSTALL_OPTIONAL_MEDIA" = "true" ]; then \
      pip install --no-cache-dir -r requirements-media.txt; \
    fi

COPY . .
COPY --from=mkaos-rust-build /src/engine/mkaos-inference/target/release/mkaos-generate /usr/local/bin/mkaos-generate

RUN mkdir -p /app/memory/personal /app/memory/universe /app/memory/universe_kb /app/memory/generated_images /app/memory/voice /app/models/voices /app/models/whisper-small /app/models/mkaos

EXPOSE 8000

CMD ["python", "-m", "scripts.run", "web", "--host", "0.0.0.0", "--port", "8000"]
