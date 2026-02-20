#!/bin/bash
# Porniți scraper-ul intern NodeJS Torrentio (ascultă pe portul 7000 intern)
echo "Pornim Torrentio Scraper intern..."
cd /scraper && node index.js &

# Porniți Torrenthan
echo "Pornim Torrenthan..."
cd /app && uvicorn main:app --host 0.0.0.0 --port ${PORT:-7002}
