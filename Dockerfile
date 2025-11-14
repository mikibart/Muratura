# Muratura FEM - Docker Image
# Multi-stage build per ottimizzare dimensione

FROM python:3.10-slim as builder

# Variabili ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directory di lavoro
WORKDIR /app

# Installa dipendenze di sistema per build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e installa dipendenze Python
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage finale (più leggera)
FROM python:3.10-slim

# Variabili ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Installa solo runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

# Directory di lavoro
WORKDIR /app

# Copia dipendenze Python installate
COPY --from=builder /root/.local /root/.local

# Copia codice sorgente
COPY Material/ ./Material/
COPY examples/ ./examples/
COPY setup.py README.md LICENSE ./

# Installa il package
RUN pip install --user -e .

# User non-root per sicurezza
RUN useradd -m -u 1000 muratura && \
    chown -R muratura:muratura /app
USER muratura

# Entry point
CMD ["python"]

# Labels
LABEL maintainer="Muratura FEM Contributors"
LABEL version="6.1.0"
LABEL description="Sistema di calcolo strutturale FEM per murature NTC 2018"
