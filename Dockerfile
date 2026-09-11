# Single-container deployment: FastAPI serves both the JSON API and the
# HTML frontend (templates/static), so one deploy covers both requirements.
FROM python:3.12-slim

# System deps: tesseract for OCR, poppler for pdf rendering fallback
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY frontend ./frontend

WORKDIR /app/backend

# Render/Railway/Koyeb set $PORT at runtime; default to 8000 for local docker run
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
