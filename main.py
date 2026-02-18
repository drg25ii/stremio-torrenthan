import os
import re
import asyncio
from urllib.parse import unquote, quote

import uvicorn
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Import moduli interni
from utils.encoding import decode_config
from core.torrentio import fetch_torrentio_streams
from core.filter import is_italian_content
from core import rd

app = FastAPI()

# Configurazione CORS
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
    magnet = f"magnet:?xt=urn:btih:{hash_val}&dn=video"
    for tr in TRACKERS:
        magnet += f"&tr={quote(tr)}"
    return magnet

# --- PARSING E UTILITÀ ---
def parse_size_to_gb(size_str: str) -> float:
    if not size_str or size_str == "N/A": 
        return 0.0
    match = re.search(r'([\d\.]+)\s*([GM]B)', size_str, re.IGNORECASE)
    if not match: 
        return 0.0
    value = float(match.group(1))
    unit = match.group(2).upper()
    return value / 1024 if "MB" in unit else value  

def extract_leviathan_data(title: str, name: str):
    title_lower = title.lower()
    name_lower = name.lower()
    
    res = "SD"
    if "2160p" in name_lower or "4k" in name_lower: res = "4K"
    elif "1080p" in name_lower: res = "1080p"
    elif "720p" in name_lower: res = "720p"

    codec = "x264"
    if "hevc" in title_lower or "h265" in title_lower: codec = "HEVC"
    elif "avc" in title_lower or "h264" in title_lower: codec = "AVC"

    hdr_tag = ""
    if "dv" in title_lower or "dolby vision" in title_lower: hdr_tag += " • DV"
    if "hdr" in title_lower: hdr_tag += " • HDR"
    
    audio = "AAC"
    if "ddp" in title_lower or "eac3" in title_lower: audio = "Dolby DDP"
    elif "ac3" in title_lower or "dd5.1" in title_lower: audio = "Dolby Digital"
    elif "truehd" in title_lower: audio = "TrueHD"
    elif "dts" in title_lower: audio = "DTS"

    peers_match = re.search(r"👤\s*(\d+)", title)
    peers = peers_match.group(1) if peers_match else "0"
    size_match = re.search(r"💾\s*([\d\.]+\s*[GM]B)", title)
    size = size_match.group(1) if size_match else "N/A"
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
    return match.group(1).lower() if match else ""

# --- LOGICHE DI RISOLUZIONE ---
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
                links = info.get('links', [])
                if links:
                    unrestrict_resp = await client.post("https://api.real-debrid.com/rest/1.0/unrestrict/link", data={"link": links[0]})
                    if unrestrict_resp.status_code == 200:
                        return unrestrict_resp.json().get('download')
    except Exception as e: print(f"RD Resolve Error: {e}")
    return None

async def logic_get_torbox_link(hash_val: str, api_key: str):
    if not hash_val: return None
    base_url = "https://api.torbox.app/v1/api"
    headers = {"Authorization": f"Bearer {api_key}"}
    full_magnet = get_magnet_with_trackers(hash_val)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{base_url}/torrents/createtorrent", data={"magnet": full_magnet}, headers=headers)
            resp_list = await client.get(f"{base_url}/torrents/mylist?bypass_cache=true", headers=headers)
            target = next((t for t in resp_list.json().get('data', []) if t.get('hash') == hash_val), None)
            if target and target.get('files'):
                params = {"token": api_key, "torrent_id": target['id'], "file_id": target['files'][0]['id'], "zip_link": "false"}
                resp_dl = await client.get(f"{base_url}/torrents/requestdl", params=params, headers=headers)
                if resp_dl.status_code == 200: return resp_dl.json().get('data')
    except Exception as e: print(f"TB Resolve Error: {e}")
    return None

# --- ENDPOINTS ---
MANIFEST = {
    "id": "org.ita.torrenthan",
    "version": "1.0.0",
    "name": "Torrenthan 🇮🇹",
    "description": "L'esperienza definitiva per lo streaming in Italia. Ottimizzato per Real-Debrid e TorBox.",
    "logo": "https://i.ibb.co/wfF4j52/Gemini-Generated-Image-mm5p80mm5p80mm5p-Photoroom.png",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "catalogs": [],
    "idPrefixes": ["tt", "kitsu"]
}

@app.get("/", response_class=HTMLResponse)
@app.get("/configure", response_class=HTMLResponse)
async def configure(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})

@app.get("/manifest.json")
async def get_manifest_no_config():
    return MANIFEST

@app.get("/{config}/manifest.json")
async def get_manifest(config: str):
    return MANIFEST

@app.get("/{config}/playback/{service}/{query}/{filename}")
async def playback(config: str, service: str, query: str, filename: str):
    settings = decode_config(config)
    apikey = settings.get("key")
    final_url = await logic_get_rd_link(query, apikey) if service == 'realdebrid' else await logic_get_torbox_link(query, apikey)
    if final_url: return RedirectResponse(url=final_url)
    return JSONResponse(status_code=404, content={"error": "Link non disponibile"})

@app.get("/{config}/stream/{type}/{id}.json")
async def get_stream(request: Request, config: str, type: str, id: str):
    settings = decode_config(config)
    service, apikey = settings.get("service"), settings.get("key")
    excluded_qualities = settings.get("qualityfilter", "").split(",")
    size_limit = float(settings.get("sizelimit", 0))

    # --- DEBUG LOGS (Verifica Torrentio) ---
    print(f"[DEBUG] Richiesta stream per ID: {id}, Tipo: {type}")
    
    try:
        data = await fetch_torrentio_streams(type, id, settings.get("options", ""))
        streams = data.get("streams", [])
        print(f"[DEBUG] Torrentio ha restituito {len(streams)} risultati grezzi.")
    except Exception as e:
        print(f"[DEBUG ERROR] Errore chiamata Torrentio: {e}")
        return {"streams": []}

    final_streams = []
    # Filtraggio per lingua italiana
    ita_streams = [s for s in streams if is_italian_content(s.get('name', ''), s.get('title', ''))]
    print(f"[DEBUG] Dopo il filtro ITA sono rimasti {len(ita_streams)} risultati.")

    host_url = f"{request.url.scheme}://{request.url.netloc}"
    checks = {"4k": ["4k", "2160p"], "1080p": ["1080p"], "720p": ["720p"], "hdr": ["hdr"], "hevc": ["hevc", "x265"]}

    for stream in ita_streams:
        combined_text = (stream.get('name', '') + " " + stream.get('title', '')).lower()
        if any(q in checks and any(x in combined_text for x in checks[q]) for q in excluded_qualities): continue

        info_hash = get_hash_from_stream(stream)
        data = extract_leviathan_data(stream.get('title', ''), stream.get('name', ''))
        
        if size_limit > 0 and parse_size_to_gb(data['size']) > size_limit: continue

        provider_code, provider_icon, left_icon = ("RD", "⚡", "👑") if service == 'realdebrid' else ("TB", "⚡", "🧊") if service == 'torbox' else ("P2P", "👤", "🔵")
        
        if apikey and (service == 'realdebrid' or service == 'torbox'):
            stream['url'] = f"{host_url}/{config}/playback/{service}/{info_hash}/video.mp4"
            stream['behaviorHints'] = {'notWebReady': True}

        # Pulizia titolo per Stremio
        raw_title = stream.get('title', '').split('\n')[0]
        stream['name'] = f"{left_icon} {provider_code} {provider_icon}\nTorrenthan"
        stream['title'] = (
            f"▶ {raw_title}\n"
            f"🔱 {data['res']} • {data['codec']}{data['hdr']}\n"
            f"🗣️ IT/GB • 💿 {data['audio']}\n"
            f"💾 {data['size']} • 👥 {data['peers']}"
        )
        final_streams.append(stream)

    print(f"[DEBUG] Invio a Stremio {len(final_streams)} stream finali.")
    return {"streams": sorted(final_streams[:20], key=lambda x: "⚡" not in x["name"])}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
