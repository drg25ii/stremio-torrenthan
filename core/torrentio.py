import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Schimbăm instanța principală cu una de rezervă (ex: torrentio-lite sau ElfHosted)
# care are reguli de firewall mult mai blânde pentru serverele de tip cloud.
TORRENTIO_URL = "https://torrentio-lite.strem.fun"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    # Construim url-ul final
    base_path = f"/{options}" if options else ""
    url = f"{TORRENTIO_URL}{base_path}/stream/{type}/{id}.json"
    
    # Adăugăm un User-Agent realist pentru a părea că suntem un browser sau aplicație Stremio
    # și nu un "bot" de pe un datacenter Northflank.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        try:
            response = await client.get(url)
            # Dacă dă 403, ridicăm eroarea pentru a fi prinsă de Retry
            response.raise_for_status() 
            return response.json()
        except httpx.HTTPStatusError as e:
            # Dacă și instanța secundară e blocată, printăm statusul exact (ex: 403, 404, 429)
            print(f"HTTPStatusError: Torrentio a refuzat conexiunea. Status Code: {e.response.status_code}")
            raise e
