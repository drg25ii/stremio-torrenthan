from tenacity import retry, wait_fixed, stop_after_attempt
from curl_cffi.requests import AsyncSession

TORRENTIO_URL = "https://torrentio.strem.fun"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    
    base_path = f"/{options}" if options else ""
    url = f"{TORRENTIO_URL}{base_path}/stream/{type}/{id}.json"
    
    # curl_cffi simulează complet comportamentul Chrome (impersonate='chrome120')
    # ocolind blocajele de IP sau captchas statice de la Torrentio (Cloudflare).
    try:
        print(f"DEBUG: Cerere DIRECTA (Anti-Cloudflare TLS) către: {url}")
        
        async with AsyncSession(impersonate="chrome120") as session:
            response = await session.get(url, timeout=15)
            response.raise_for_status() 
            
            return response.json()
            
    except Exception as e:
        print(f"EROARE LA PRELUARE (CURL_CFFI): {str(e)}")
        return {"streams": []}
