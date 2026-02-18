import httpx
import random
import os
from tenacity import retry, stop_after_attempt, wait_exponential

# Rotazione User-Agent per simulare un browser reale
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
async def fetch_from_provider(client, url, headers):
    """Funzione interna per tentare la chiamata HTTP."""
    print(f"[DEBUG TORRENTHAN] Tentativo su: {url}")
    response = await client.get(url, headers=headers, timeout=15)
    
    if response.status_code == 403:
        print(f"[DEBUG ERROR] Accesso NEGATO (403) dall'IP Northflank per: {url}")
    
    response.raise_for_status()
    return response.json()

async def fetch_torrentio_streams(type: str, id: str, torrentio_options: str = ""):
    """
    Recupera i dati per Torrenthan. 
    Se l'istanza principale fallisce (403), prova automaticamente un'istanza di riserva.
    """
    # Lista di istanze da provare (puoi aggiungerne altre qui)
    instances = [
        os.getenv("TORRENTIO_URL", "https://torrentio.strem.fun"),
        "https://torrentio-lite.strem.fun" # Istanza di riserva (fallback)
    ]
    
    # Configurazione Proxy (se impostato in Northflank)
    proxy_url = os.getenv("PROXY_URL")
    proxies = {"all://": proxy_url} if proxy_url else None
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(proxies=proxies, follow_redirects=True) as client:
        for base_url in instances:
            # Costruisci l'URL
            if torrentio_options:
                url = f"{base_url}/{torrentio_options}/stream/{type}/{id}.json"
            else:
                url = f"{base_url}/stream/{type}/{id}.json"

            try:
                data = await fetch_from_provider(client, url, headers)
                if data and data.get("streams"):
                    print(f"[DEBUG SUCCESS] Dati ricevuti correttamente da: {base_url}")
                    return data
            except Exception as e:
                print(f"[DEBUG INFO] Fallimento su {base_url}, provo la prossima istanza...")
                continue
        
        # Se tutte le istanze falliscono
        print("[DEBUG CRITICAL] Tutte le fonti hanno fallito l'invio dati a Torrenthan.")
        return {"streams": []}
