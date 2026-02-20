FROM python:3.11-slim

# Imposta la directory di lavoro nel container
WORKDIR /app

# Variabili d'ambiente per evitare file .pyc e buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Setăm un port default pentru teste locale
ENV PORT=7002

# Copia prima i requirements per sfruttare la cache di Docker
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice sorgente
COPY . .

# Espone la porta
EXPOSE 7002

# Comando di avvio (citind variabila $PORT alocată de Northflank)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
