import httpx
from tenacity import retry, wait_fixed, stop_after_attempt

# Instanța oficială Torrentio (ținta finală)
TORRENTIO_URL = "https://torrentio.strem.fun"

# Proxy-ul tău de pe Koyeb formatat cu parola (Basic Auth)
# Folosim formatul httpx: http://username:password@host:port (pentru proxy-uri simple lăsăm username gol)
PROXY_URL = "https://:Inter2010@outrageous-orel-drg25ii-d3f3490c.koyeb.app"

@retry(wait=wait_fixed(1), stop=stop_after_attempt(2))
async def fetch_torrentio_streams(type: str, id: str, options: str = "") -> dict:
    
    # 1. Construim URL-ul cererii finale
    base_path = f"/{options}" if options else ""
    url = f"{TORRENTIO_URL}{base_path}/stream/{type}/{id}.json"
    
    # 2. Setăm User-Agent ca să arătăm ca un browser normal
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json"
    }

    # 3. Configurăm rutele de proxy pentru ambele protocoale HTTP și HTTPS
    proxies = {
        "http://": PROXY_URL,
        "https://": PROXY_URL
    }

    # 4. Trimitem cererea folosind proxy-ul Koyeb
    async with httpx.AsyncClient(timeout=20.0, headers=headers, proxies=proxies) as client:
        try:
            print(f"DEBUG: Trimitere cerere prin PROXY Koyeb către: {url}")
            response = await client.get(url)
            
            # Verificăm dacă Torrentio tot ne dă eroare (ex: 403, 404)
            response.raise_for_status() 
            
            data = response.json()
            
            if "streams" in 
                print(f"SUCCES PROXY! Am primit {len(data['streams'])} rezultate brute de la Torrentio.")
            else:
                print("DEBUG: Torrentio a răspuns, dar lista e goală.")
                
            return data
            
        except httpx.HTTPStatusError as e:
            print(f"EROARE HTTPStatus: Torrentio a refuzat cererea proxy-ului (Status: {e.response.status_code})")
            return {"streams": []}
        except httpx.ConnectError:
            print(f"EROARE Connect: Nu m-am putut conecta la proxy-ul Koyeb!")
            return {"streams": []}
        except Exception as e:
            print(f"EROARE GENERALĂ LA PRELUARE: {str(e)}")
            return {"streams": []}
