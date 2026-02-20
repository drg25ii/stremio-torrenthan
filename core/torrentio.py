import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

COMET_URL = "https://comet.elfhosted.com"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    url = f"{COMET_URL}/stream/{type}/{id}.json"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            print(f"CERERE COMET ELFHOSTED: {url}")
            response = await client.get(url)
            response.raise_for_status() 
            
            # Preluăm direct dicționarul. Dacă nu are 'streams', returnăm lista goală.
            return response.json()
            
        except Exception as e:
            print(f"EROARE LA PRELUARE: {str(e)}")
            return {"streams": []}
