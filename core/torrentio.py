import httpx
import random
import os
from tenacity import retry, stop_after_attempt, wait_exponential

# User-Agents variate pentru a simula trafic real
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
async def fetch_from_provider(client, url, headers):
    """Încearcă să preia datele de la furnizor."""
    print(f"[DEBUG TORRENTHAN] Connessione a: {url}")
    response = await client.get(url, headers=headers, timeout=12)
    
    if response.status_code == 403:
        print(f"[DEBUG ERROR] 403 Forbidden su: {url}")
    
    response.raise_for_status()
    return response.json()

async def fetch_torrentio_streams(type: str, id: str, torrentio_options: str = ""):
    """
    Recupera i dati per Torrenthan utilizzando più sorgenti (Comet + Torrentio).
    """
    # Verifică dacă există un Proxy setat în Northflank
    proxy_url = os.getenv("PROXY_URL")
    proxies = {"all://": proxy_url} if proxy_url else None
    
    # Listă de instanțe: Comet este prima deoarece are reputație mai bună pentru Cloud
    instances = [
        "https://comet.strem.fun", # Sursă alternativă stabilă
        os.getenv("TORRENTIO_URL", "https://torrentio.strem.fun"),
        "https://torrentio-lite.strem.fun"
    ]
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(proxies=proxies, follow_redirects=True, verify=False) as client:
        for base_url in instances:
            # Construiește URL-ul în funcție de instanță (Comet are format similar)
            if torrentio_options:
                url = f"{base_url}/{torrentio_options}/stream/{type}/{id}.json"
            else:
                url = f"{base_url}/stream/{type}/{id}.json"

            try:
                data = await fetch_from_provider(client, url, headers)
                if data and data.get("streams"):
                    print(f"[DEBUG SUCCESS] Torrenthan ha ricevuto dati da: {base_url}")
                    return data
            except Exception as e:
                print(f"[DEBUG INFO] Sorgente {base_url} non disponibile. Provo la prossima...")
                continue
        
        print("[DEBUG CRITICAL] Northflank è completamente bloccato. Usa PROXY_URL o MediaFlow.")
        return {"streams": []}
