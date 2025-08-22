# Dockerfile for Cloud Firestore Crypto Access Backend
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TZ=Asia/Ho_Chi_Minh
ENV FLASK_ENV=production
ENV HOST=0.0.0.0
ENV PORT=5000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    libssl-dev \
    libffi-dev \
    pkg-config \
    curl \
    wget \
    gcc \
    g++ \
    make \
    cmake \
    libgmp-dev \
    libpbc-dev \
    flex \
    bison \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p log tmp uploads abe_keys env && \
    touch log/.gitkeep tmp/.gitkeep uploads/.gitkeep

# Set permissions for app user
RUN chown -R app:app /app && \
    chmod +x lib/libhybrid-cp-abe.so 2>/dev/null || true

# Switch to non-root user for security
USER app

# Expose application port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/ca/health || exit 1

# Use Python to run the application directly
CMD ["python3", "-u", "main.py"]
