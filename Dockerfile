# Any2MD — slim image for serve mode (Docker / Railway).
FROM python:3.11-slim

# System deps: ffmpeg for yt-dlp Whisper fallback, tesseract for image OCR via markitdown.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install the package plus the optional serve extras (fastapi + uvicorn).
RUN pip install --no-cache-dir ".[serve]"

# Conversions are written here; mount a volume to persist.
ENV ANY2MD_OUTPUT_DIR=/data
RUN mkdir -p /data

EXPOSE 8000
ENTRYPOINT ["any2md"]
# Default: serve mode. Railway overrides the port via $PORT (see railway.toml).
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
