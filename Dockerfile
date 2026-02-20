FROM python:3.11-slim

# 1. Instalăm Node.js și wget pentru scraperul intern Torrentio
RUN apt-get update && apt-get install -y curl wget gnupg2 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs git \
    && rm -rf /var/lib/apt/lists/*

# 2. Descărcăm și instalăm Torrentio Scraper (în fundal)
WORKDIR /scraper
RUN git clone https://github.com/TheBeastLT/torrentio-scraper.git . \
    && npm install

# 3. Pregătim Torrenthan (aplicația ta)
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7002

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiem tot codul tău
COPY . .

# 5. Facem scriptul de start executabil
RUN chmod +x start.sh

EXPOSE 7002

CMD ["./start.sh"]
