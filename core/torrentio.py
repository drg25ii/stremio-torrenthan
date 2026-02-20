import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Folosim varianta găzduită de ElfHosted, care are DNS-uri mult mai bine propagate la nivel global.
COMET_URL = "https://comet.elfhosted.com"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    url = f"{COMET_URL}/stream/{type}/{id}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json"
    }

    # Creștem timeout-ul la 30s pentru că uneori DNS-ul în containere Docker are lag la rezolvare.
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        try:
            print(f"CERERE CATRE: {url}")
            response = await client.get(url)
            response.raise_for_status() 
            
            data = response.json()
            # Dacă sursa dă rezultate bune, le returnăm
            if "streams" in 
                print(f"SUCCES: Am primit {len(data['streams'])} stream-uri.")
                return data
            return {"streams": []}
            
        except Exception as e:
            print(f"EROARE LA PRELUARE: {str(e)}")
            return {"streams": []}
