#!/bin/bash
# Porniți scraper-ul Comet în fundal (ascultă intern pe 8000)
echo "Pornim Comet intern..."
python /comet/comet/main.py &

# Porniți Torrenthan (FastAPI-ul tău care ascultă pe portul Northflank)
echo "Pornim Torrenthan..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-7002}
