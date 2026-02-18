import httpx
import random
import os
from tenacity import retry, stop_after_attempt, wait_exponential

# Rotazione User-Agent per evitare blocchi
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_torrentio_streams(type: str, id: str, torrentio_options: str = ""):
    """
    Scarica gli stream da Torrentio con supporto Proxy per Northflank.
    """
    # 1. Recupera l'istanza Torrentio (puoi cambiarla con una lite se necessario)
    base_url = os.getenv("TORRENTIO_URL", "https://torrentio.strem.fun")
    
    # 2. Costruisci l'URL finale
    if torrentio_options:
        url = f"{base_url}/{torrentio_options}/stream/{type}/{id}.json"
    else:
        url = f"{base_url}/stream/{type}/{id}.json"

    # 3. Configurazione Proxy (OPZIONALE)
    # Se hai un MediaFlow Proxy o un altro proxy HTTP, impostalo in Northflank
    proxy_url = os.getenv("PROXY_URL") # Esempio: http://user:pass@host:port
    proxies = {"all://": proxy_url} if proxy_url else None

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    print(f"[DEBUG TORRENTIO] Chiamata a: {url}")

    async with httpx.AsyncClient(timeout=20, proxies=proxies, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        
        # Log del codice di stato per debug in Northflank
        print(f"[DEBUG TORRENTIO] Status Code: {response.status_code}")
        
        if response.status_code == 403:
            print("[CRITICAL] L'IP di Northflank è BLOCCATO da Torrentio (403 Forbidden)")
        
        response.raise_for_status()
        return response.json()
