import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Adresa către Torrentio pe care vrem s-o accesăm
TARGET_URL = "https://torrentio.strem.fun"

# Adresa proxy-ului tău EasyProxy de pe Koyeb
EASYPROXY_URL = "https://outrageous-orel-drg25ii-d3f3490c.koyeb.app"

# Parola setată de tine pentru EasyProxy
EASYPROXY_PASS = "Inter2010"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    
    # 1. Construim calea pe care o dorim de la Torrentio (ex: /stream/movie/tt1234.json)
    base_path = f"/{options}" if options else ""
    target_path = f"{base_path}/stream/{type}/{id}.json"
    
    # 2. Construim URL-ul complet formatat pentru EasyProxy/MediaFlow
    # EasyProxy/MediaFlow iau de obicei URL-ul țintă și parola în link
    # Format standard proxy Stremio: https://[PROXY]/proxy/[PAROLA]/[URL_TINTA]
    url = f"{EASYPROXY_URL}/proxy/{EASYPROXY_PASS}/{TARGET_URL}{target_path}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # FĂRĂ parametrul "proxies" - facem o cerere HTTP normală direct către Koyeb!
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        try:
            print(f"CERERE PRIN EASYPROXY: {url}")
            response = await client.get(url)
            
            # Verificăm dacă primim eroare 400 de la EasyProxy sau 403 de la Torrentio
            response.raise_for_status() 
            
            return response.json()
            
        except Exception as e:
            print(f"EROARE LA PRELUARE (EASYPROXY): {str(e)}")
            return {"streams": []}
