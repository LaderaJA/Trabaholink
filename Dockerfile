# Multi-stage Dockerfile for Trabaholink Django Application
# Stage 1: Base image with system dependencies
FROM python:3.11-slim-bookworm as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for GeoDjango, PostGIS, OCR, and CV
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    cmake \
    pkg-config \
    # PostgreSQL client and development files
    postgresql-client \
    libpq-dev \
    # GDAL for GeoDjango
    gdal-bin \
    libgdal-dev \
    # GEOS for GeoDjango
    libgeos-dev \
    # PROJ for GeoDjango
    libproj-dev \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # Image processing libraries
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    # OpenCV dependencies
    libopencv-dev \
    python3-opencv \
    # dlib dependencies
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    # ZBar for QR code reading
    libzbar0 \
    libzbar-dev \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    # Other utilities
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
# Find the actual GDAL library path and create symlink
RUN GDAL_LIB=$(find /usr/lib -name "libgdal.so*" | head -n 1) && \
    if [ -n "$GDAL_LIB" ]; then \
        ln -sf "$GDAL_LIB" /usr/lib/libgdal.so; \
    fi

ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so \
    GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so 

WORKDIR /app

# Stage 2: Python dependencies
FROM base as python-deps

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with optimization flags
# Increase timeout for slow networks
ENV PIP_DEFAULT_TIMEOUT=300

RUN pip install --upgrade pip setuptools wheel && \
    # Install all dependencies with retries
    pip install --no-cache-dir --retries 5 -r requirements.txt

# Install Playwright browsers only (dependencies already in base stage)
RUN playwright install chromium

# Stage 3: Final production image
FROM base as production

# Create app user for security (non-root)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Python packages from python-deps stage
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin
COPY --from=python-deps /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/staticfiles /app/media /app/mediafiles /app/logs && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser/.cache

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port for Daphne
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "Trabaholink.asgi:application"]
