FROM python:3.11-slim

# Instalăm git și gcc pentru a putea descărca Comet
RUN apt-get update && apt-get install -y git build-essential gcc wget && rm -rf /var/lib/apt/lists/*

# 1. INSTALĂM DEPENDENȚELE TORRENTHAN MAI ÎNTÂI
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7002

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. INSTALĂM DEPENDENȚELE COMET (fără fișier separat)
RUN pip install --no-cache-dir uvicorn fastapi httpx tenacity pydantic "motor[asyncio]" "bencode.py" "RTN"

# 3. DESCĂRCĂM CODUL COMET ÎNTR-UN FOLDER SEPARAT
RUN git clone https://github.com/g0ldyy/comet.git /comet

# 4. COPIEM CODUL TĂU TORRENTHAN
COPY . .

# Facem scriptul de start executabil
RUN chmod +x start.sh

EXPOSE 7002

# 5. PORNIM AMBELE APLICAȚII DIN SCRIPTUL SH
CMD ["./start.sh"]
