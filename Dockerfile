FROM python:3.11-slim

# Instalăm dependențele necesare pentru Comet (git, gcc, etc)
RUN apt-get update && apt-get install -y git build-essential gcc wget && rm -rf /var/lib/apt/lists/*

# 1. DESCĂRCĂM ȘI PREGĂTIM COMET (Scraperul intern P2P)
WORKDIR /comet
RUN git clone https://github.com/g0ldyy/comet.git .
RUN pip install --no-cache-dir -r requirements.txt

# 2. PREGĂTIM TORRENTHAN (Aplicația ta FastAPI)
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7002

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Facem scriptul de start executabil
RUN chmod +x start.sh

EXPOSE 7002

# 3. PORNIREA AMBELOR SERVICII (Wrapper-ul)
CMD ["./start.sh"]
