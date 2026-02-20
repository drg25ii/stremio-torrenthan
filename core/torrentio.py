import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Cerem rezultatele direct din propria noastră mașină, ocolind blocajele Cloudflare!
# Nu mai depindem de elfhosted sau strem.fun.
COMET_URL = "http://127.0.0.1:8000"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    url = f"{COMET_URL}/stream/{type}/{id}.json"
    headers = {"User-Agent": "TorrenthanWrapper/1.0"}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            print(f"CERERE COMET INTERN: {url}")
            response = await client.get(url)
            response.raise_for_status() 
            
            return response.json()
        except Exception as e:
            print(f"EROARE LA PRELUARE INTERNĂ: {str(e)}")
            return {"streams": []}
