import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Folosim o instanță de Comet (comet.strem.fun) care este foarte indulgentă
# cu traficul ce vine de pe serverele Cloud (precum Northflank / HuggingFace).
COMET_URL = "https://comet.strem.fun"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    
    # Construim URL-ul pentru Comet.
    url = f"{COMET_URL}/stream/{type}/{id}.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        try:
            print(f"DEBUG: Se trimite cererea către: {url}")
            response = await client.get(url)
            response.raise_for_status() 
            
            comet_data = response.json()
            
            # Verificăm dacă răspunsul are streams
            if "streams" in comet_
                print(f"DEBUG: Comet a returnat {len(comet_data['streams'])} rezultate pentru {id}")
                return comet_data
            
            print("DEBUG: Răspuns valid 200, dar fără streams de la Comet.")
            return {"streams": []}

        except httpx.HTTPStatusError as e:
            print(f"HTTPStatusError: Serverul a refuzat conexiunea (Status: {e.response.status_code})")
            raise e
        except httpx.ConnectError as e:
            print("ConnectError: Nu s-a putut stabili conexiunea cu sursa.")
            raise e
        except Exception as e:
            print(f"Eroare necunoscută la preluarea datelor: {str(e)}")
            raise e
