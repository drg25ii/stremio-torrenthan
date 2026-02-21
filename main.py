from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import re
import asyncio
from urllib.parse import unquote, quote

# Import moduli interni
from utils.encoding import decode_config
from core.torrentio import fetch_torrentio_streams
from core.filter import is_italian_content
from core import rd

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# --- LISTA TRACKERS ---
TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonoid.ch:6969/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.therarbg.to:6969/announce",
    "udp://tracker.doko.moe:6969/announce",
    "udp://opentracker.i2p.rocks:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.moeking.me:6969/announce"
]

def get_magnet_with_trackers(hash_val: str):
    """Genera un magnet link completo con tutti i tracker per massimizzare i peer."""
    magnet = f"magnet:?xt=urn:btih:{hash_val}&dn=video"
    for tr in TRACKERS:
        magnet += f"&tr={quote(tr)}"
    return magnet

# --- PARSING E UTILITÀ ---

def parse_size_to_gb(size_str: str) -> float:
    """Converte stringhe come '2.5 GB' o '700 MB' in float GB."""
    if not size_str or size_str == "N/A": 
        return 0.0
    
    
    match = re.search(r'([\d\.]+)\s*([GM]B)', size_str, re.IGNORECASE)
    if not match: 
        return 0.0
        
    value = float(match.group(1))
    unit = match.group(2).upper()
    
    if "MB" in unit:
        return value / 1024  
    return value  

def extract_leviathan_data(title: str, name: str):
    title_lower = title.lower()
    name_lower = name.lower()
    
    # 1. Risoluzione
    res = "UNK"
    if "2160p" in name_lower or "4k" in name_lower: res = "4K"
    elif "1080p" in name_lower: res = "1080p"
    elif "720p" in name_lower: res = "720p"
    elif "480p" in name_lower: res = "SD"

    # 2. Codec e Video Features
    codec = "x264"
    if "hevc" in title_lower or "h265" in title_lower: codec = "HEVC"
    elif "avc" in title_lower or "h264" in title_lower: codec = "AVC"

    hdr_tag = ""
    if "dv" in title_lower or "dolby vision" in title_lower: hdr_tag += " • DV"
    if "hdr" in title_lower: hdr_tag += " • HDR"
    
    # 3. Audio
    audio = "AAC"
    if "ddp" in title_lower or "eac3" in title_lower: audio = "Dolby DDP"
    elif "ac3" in title_lower or "dd5.1" in title_lower: audio = "Dolby Digital"
    elif "truehd" in title_lower: audio = "TrueHD"
    elif "dts" in title_lower: audio = "DTS"

    # 4. Numeri
    peers_match = re.search(r"👤\s*(\d+)", title)
    peers = peers_match.group(1) if peers_match else "0"
    
    size_match = re.search(r"💾\s*([\d\.]+\s*[GM]B)", title)
    size = size_match.group(1) if size_match else "N/A"

    # 5. Uploader
    uploader_match = re.search(r"⚙️\s*([^\n]+)", title)
    uploader = uploader_match.group(1).strip() if uploader_match else "Torrentio"

    return {
        "res": res, "source": "WEB-DL" if "web" in title_lower else "Bluray", 
        "codec": codec, "hdr": hdr_tag, "audio": audio, 
        "peers": peers, "size": size, "uploader": uploader
    }

def get_hash_from_stream(stream: dict) -> str:
    if stream.get('infoHash'): return stream['infoHash'].lower()
    url = stream.get('url', '')
    match = re.search(r'btih:([a-fA-F0-9]{40})', url, re.IGNORECASE)
    if match: return match.group(1).lower()
    return ""

# --- LOGICHE DI RISOLUZIONE (LAZY RESOLVING) ---

async def logic_get_rd_link(hash_val: str, api_key: str):
    if not hash_val: return None
    full_magnet = get_magnet_with_trackers(hash_val)

    try:
        async with httpx.AsyncClient(timeout=20, headers={'Authorization': f"Bearer {api_key}"}) as client:
            payload = {'magnet': full_magnet, 'host': 'rd'}
            resp = await client.post("https://api.real-debrid.com/rest/1.0/torrents/addMagnet", data=payload)
            magnet_resp = resp.json()
            
            if 'id' not in magnet_resp: return None
            torrent_id = magnet_resp['id']
            
            await rd.select_files(client, torrent_id, "all")
            info = await rd.get_torrent_info(client, torrent_id)
            
            if info.get('status') == 'downloaded':
                files = [f for f in info.get('files', []) if f['selected'] == 1]
                files.sort(key=lambda x: x['bytes'], reverse=True)
                
                if files:
                    links = info.get('links', [])
                    if links:
                        unrestrict_resp = await client.post("https://api.real-debrid.com/rest/1.0/unrestrict/link", 
                                                          data={"link": links[0]})
                        if unrestrict_resp.status_code == 200:
                            await rd.delete_torrent(client, torrent_id)
                            return unrestrict_resp.json().get('download')
            
            await rd.delete_torrent(client, torrent_id)
    except Exception as e:
        print(f"RD Resolve Error: {e}")
    return None

async def logic_get_torbox_link(hash_val: str, api_key: str):
    if not hash_val: return None
    base_url = "https://api.torbox.app/v1/api"
    headers = {"Authorization": f"Bearer {api_key}"}
    full_magnet = get_magnet_with_trackers(hash_val)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            form = {"magnet": full_magnet, "seed": "1", "allow_zip": "false"}
            await client.post(f"{base_url}/torrents/createtorrent", data=form, headers=headers)
            
            resp_list = await client.get(f"{base_url}/torrents/mylist?bypass_cache=true", headers=headers)
            if resp_list.status_code != 200: return None
            
            my_torrents = resp_list.json().get('data', [])
            target = next((t for t in my_torrents if t.get('hash') == hash_val), None)
            
            if not target: return None
            
            torrent_id = target.get('id')
            files = target.get('files', [])
            files.sort(key=lambda x: x.get('size', 0), reverse=True)
            if not files: return None
            
            file_id = files[0].get('id')
            params = {"token": api_key, "torrent_id": torrent_id, "file_id": file_id, "zip_link": "false"}
            resp_dl = await client.get(f"{base_url}/torrents/requestdl", params=params, headers=headers)
            if resp_dl.status_code == 200:
                data = resp_dl.json()
                if data.get('success'): return data.get('data') 
    except Exception as e:
        print(f"TB Resolve Error: {e}")
    return None

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
@app.get("/configure", response_class=HTMLResponse)
async def configure(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})

@app.get("/{config}/manifest.json")
async def get_manifest(config: str):
    return {
        "id": "org.ita.torrenthan",
        "version": "1.0.0",
        "name": "Torrenthan 🇮🇹",
        "description": "L'esperienza definitiva per lo streaming in Italia. Torrenthan ottimizza Torrentio con supporto avanzato per Real-Debrid e TorBox, caricamento istantaneo (Lazy Loading) e tracker personalizzati per una stabilità senza precedenti.",
        "logo": "https://i.ibb.co/wfF4j52/Gemini-Generated-Image-mm5p80mm5p80mm5p-Photoroom.png",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "catalogs": [],
        "idPrefixes": ["tt", "kitsu"]
    }

@app.get("/{config}/playback/{service}/{query}/{filename}")
async def playback(config: str, service: str, query: str, filename: str):
    settings = decode_config(config)
    apikey = settings.get("key")
    final_url = None

    if service == 'realdebrid' and apikey:
        final_url = await logic_get_rd_link(query, apikey)
    elif service == 'torbox' and apikey:
        final_url = await logic_get_torbox_link(query, apikey)

    if final_url:
        return RedirectResponse(url=final_url)
    return JSONResponse(status_code=404, content={"error": "Link non disponibile o risoluzione fallita"})

@app.get("/{config}/stream/{type}/{id}.json")
async def get_stream(request: Request, config: str, type: str, id: str):
    settings = decode_config(config)
    service = settings.get("service")
    apikey = settings.get("key")
    options = settings.get("options", "")
    
    # --- RECUPERO FILTRI DALLA CONFIGURAZIONE ---
    excluded_qualities = settings.get("qualityfilter", "").split(",")
    # Recupera il limite di dimensione, default 0 (nessun limite)
    size_limit = float(settings.get("sizelimit", 0))

    try:
        data = await fetch_torrentio_streams(type, id, options)
        streams = data.get("streams", [])
    except: return {"streams": []}

    final_streams = []
    ita_streams = [s for s in streams if is_italian_content(s.get('name', ''), s.get('title', ''))]
    host_url = f"{request.url.scheme}://{request.url.netloc}"

    # --- DEFINIZIONE KEYWORDS PER IL FILTRAGGIO QUALITÀ ---
    checks = {
        "cam": ["cam", "ts", "telesync", "hd-ts", "hdts", "tc"],
        "scr": ["scr", "screener", "dvdscr", "bdscr"],
        "3d": ["3d", "sbs", "hou", "half-sbs"],
        "4k": ["4k", "2160p", "uhd"],
        "1080p": ["1080p", "fhd"],
        "720p": ["720p", "hd"],
        "hdr": ["hdr", "hdr10", "hdr10+"],
        "dolbyvision": ["dv", "dolby vision", "dovi"],
        "hevc": ["hevc", "x265", "h265"]
    }

    for stream in ita_streams:
        original_name = stream.get('name', '')
        original_title = stream.get('title', '')
        combined_text = (original_name + " " + original_title).lower()

        # --- APPLICAZIONE FILTRO QUALITÀ ---
        should_exclude = False
        for q in excluded_qualities:
            if q in checks:
                if any(x in combined_text for x in checks[q]):
                    should_exclude = True
                    break
        
        if should_exclude:
            continue # Salta questo stream e passa al prossimo

        # --- ESTRAZIONE DATI (per Dimensione e Formattazione) ---
        info_hash = get_hash_from_stream(stream)
        data = extract_leviathan_data(original_title, original_name)

        # --- APPLICAZIONE FILTRO DIMENSIONE (NUOVO) ---
        if size_limit > 0:
            size_gb = parse_size_to_gb(data['size'])
            
            if size_gb > 0 and size_gb > size_limit:
                continue

        # --- FORMATTAZIONE STREAM ---
        provider_code = "P2P"
        provider_icon = "👤"
        left_color_icon = "🔵"
        
        if (service == 'realdebrid' or service == 'torbox') and apikey:
            provider_code = "RD" if service == 'realdebrid' else "TB"
            provider_icon = "⚡"
            left_color_icon = "👑" if service == 'realdebrid' else "🧊️"
            stream['url'] = f"{host_url}/{config}/playback/{service}/{info_hash}/video.mp4"
            stream['behaviorHints'] = {'notWebReady': True}
            if 'infoHash' in stream: del stream['infoHash']

        stream['name'] = f"{left_color_icon} {provider_code} {provider_icon}\nTorrenthan"
        clean_filename = original_title.split('\n')[0].replace('.', ' ').strip()
        stream['title'] = (
            f"▶ {clean_filename}\n"
            f"🔱 {data['res']} • {data['source']} • {data['codec']}{data['hdr']}\n"
            f"🗣️ IT/GB | 💿 {data['audio']}\n"
            f"💾 {data['size']} | 👥 {data['peers']}\n"
            f"🔗 {data['uploader']}"
        )
        final_streams.append(stream)
    
    
    final_streams = final_streams[:20]

    final_streams.sort(key=lambda x: "⚡" not in x["name"])
    return {"streams": final_streams}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7002)
