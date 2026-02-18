FROM python:3.11-slim

# deps pentru git + (opțional) build deps dacă ai pachete care compilează
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# HF rulează ca UID 1000; evită probleme de permisiuni
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7002

WORKDIR $HOME
USER user

# Clone repo-ul
RUN git clone --depth 1 https://github.com/drg25ii/stremio-torrenthan app
WORKDIR $HOME/app

# Instalează deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 7002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7002"]
