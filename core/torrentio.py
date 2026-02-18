import httpx
import random
import os
from tenacity import retry, stop_after_attempt, wait_exponential

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
async def fetch_from_provider(client, url, headers):
    print(f"[DEBUG TORRENTHAN] Tentativo su: {url}")
    response = await client.get(url, headers=headers, timeout=15)
    
    if response.status_code == 403:
        print(f"[DEBUG ERROR] 403 Forbidden - IP Northflank BLOCCATO.")
    
    response.raise_for_status()
    return response.json()

async def fetch_torrentio_streams(type: str, id: str, torrentio_options: str = ""):
    # 1. Încearcă să folosești un proxy dacă este setat în Northflank
    # Recomandat: MediaFlow Proxy sau un Proxy rezidențial
    proxy_url = os.getenv("PROXY_URL") 
    
    # Dacă nu ai un proxy setat, acest cod va eșua pe Northflank din cauza blocării IP-ului.
    proxies = {"all://": proxy_url} if proxy_url else None
    
    # Instanțe alternative
    instances = [
        "https://torrentio.strem.fun",
        "https://torrentio-lite.strem.fun"
    ]
    
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json"}

    async with httpx.AsyncClient(proxies=proxies, follow_redirects=True) as client:
        for base_url in instances:
            url = f"{base_url}/{torrentio_options}/stream/{type}/{id}.json" if torrentio_options else f"{base_url}/stream/{type}/{id}.json"
            try:
                data = await fetch_from_provider(client, url, headers)
                if data and data.get("streams"):
                    return data
            except Exception:
                continue
        
        print("[DEBUG CRITICAL] Northflank este blocat. Ai nevoie de PROXY_URL în Environment Variables.")
        return {"streams": []}
