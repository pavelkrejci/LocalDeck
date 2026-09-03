import httpx
import asyncio
import re
from typing import Optional, Dict

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
ICON_RE = re.compile(r"<link[^>]+rel=[\"']?(?:shortcut icon|icon)[\"']?[^>]*href=[\"']([^\"']+)[\"']", re.IGNORECASE)

async def _fetch(client: httpx.AsyncClient, url: str, timeout: float):
    try:
        r = await client.get(url, follow_redirects=False, timeout=timeout)
        return r
    except Exception:
        return None

async def probe_host(host: str, port: int, timeout: float = 1.5) -> Optional[Dict]:
    # try http first, then https
    base = f"{host}:{port}"
    async with httpx.AsyncClient(verify=False, http2=True) as client:
        # try http
        url = f"http://{host}:{port}/"
        r = await _fetch(client, url, timeout)
        scheme = None
        if r is not None:
            scheme = "http"
        else:
            url = f"https://{host}:{port}/"
            r = await _fetch(client, url, timeout)
            if r is not None:
                scheme = "https"
        if r is None:
            return None
        text = r.text if hasattr(r, "text") else ""
        title = None
        m = TITLE_RE.search(text)
        if m:
            title = m.group(1).strip()
        icon = None
        m2 = ICON_RE.search(text)
        if m2:
            icon = m2.group(1)
        else:
            # fallback to /favicon.ico
            icon = f"http://{host}:{port}/favicon.ico"
        result = {
            "host": host,
            "port": port,
            "scheme": scheme,
            "status_code": r.status_code,
            "title": title,
            "icon": icon,
            "headers": dict(r.headers),
        }
        return result
