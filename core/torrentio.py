import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

TORRENTIO_URL = "https://torrentio.strem.fun"
PROXY_URL = "https://:Inter2010@outrageous-orel-drg25ii-d3f3490c.koyeb.app"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    
    base_path = f"/{options}" if options else ""
    url = f"{TORRENTIO_URL}{base_path}/stream/{type}/{id}.json"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    proxies = {"http://": PROXY_URL, "https://": PROXY_URL}

    async with httpx.AsyncClient(timeout=20.0, headers=headers, proxies=proxies) as client:
        try:
            print(f"CERERE PRIN KOYEB: {url}")
            response = await client.get(url)
            response.raise_for_status() 
            
            # Preluăm și returnăm dicționarul direct (fără "if" care să se taie)
            return response.json()
            
        except Exception as e:
            print(f"EROARE LA PRELUARE (PROXY): {str(e)}")
            return {"streams": []}
