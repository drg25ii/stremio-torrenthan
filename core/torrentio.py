import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Cerem rezultatele de la scraper-ul Node.js ascuns în container (pe port 7000)
SCRAPER_URL = "http://127.0.0.1:7000"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    url = f"{SCRAPER_URL}/stream/{type}/{id}.json"
    headers = {"User-Agent": "Torrenthan/1.0"}

    async with httpx.AsyncClient(timeout=3
