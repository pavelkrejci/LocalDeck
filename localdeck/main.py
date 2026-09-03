from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from jinja2 import Environment, PackageLoader, select_autoescape
import asyncio
import logging
import os
from .discovery import Scanner
from .models import init_db, get_session, Service, list_services
from .caddy import CaddyClient
from sqlmodel import select

logger = logging.getLogger("localdeck")
app = FastAPI()

env = Environment(
    loader=PackageLoader("localdeck", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# serve favicons and other assets from localdeck/static
app.mount("/static", StaticFiles(directory="localdeck/static"), name="static")

CADDY_ENABLED = os.environ.get("LOCALDECK_CADDY_ENABLED", "false").lower() in ("1", "true", "yes")
CADDY_ADMIN = os.environ.get("LOCALDECK_CADDY_ADMIN_URL", "http://127.0.0.1:2019")
CADDY_AUTOSYNC_INTERVAL = float(os.environ.get("LOCALDECK_CADDY_AUTOSYNC_INTERVAL", "15"))

@app.on_event("startup")
async def startup_event():
    init_db()
    scanner = Scanner()
    # store on app state so CLI or tests can access
    app.state.scanner = scanner
    # caddy client
    app.state.caddy = CaddyClient(admin_url=CADDY_ADMIN) if CADDY_ENABLED else None
    # start background tasks
    asyncio.create_task(scanner.run_background())
    if app.state.caddy:
        asyncio.create_task(_caddy_autosync_loop())

@app.get("/")
async def index(request: Request):
    template = env.get_template("index.html")
    services = list_services()
    html = template.render(services=services)
    return HTMLResponse(content=html)

@app.get("/api/services")
async def api_services():
    sess = get_session()
    return [s.dict() for s in sess.query(Service).all()]

@app.post("/api/services/{service_id}")
async def update_service(service_id: int, payload: dict):
    """Update service overrides. Accepts JSON with optional keys: name, hostname, icon, enabled, caddy_managed

    - name: user display name
    - hostname: desired hostname (must be DNS-safe)
    - icon: URL or path to icon
    - caddy_managed: boolean to force apply/remove route
    """
    sess = get_session()
    s = sess.get(Service, service_id)
    if not s:
        raise HTTPException(status_code=404, detail="service not found")
    changed = False
    if "name" in payload:
        s.name = payload.get("name")
        changed = True
    if "hostname" in payload:
        # basic validation: only allow a-z0-9- and dot
        import re
        hn = payload.get("hostname") or ""
        if not re.match(r"^[a-z0-9\-\.]+$", hn):
            raise HTTPException(status_code=400, detail="invalid hostname")
        s.hostname = hn
        changed = True
    if "icon" in payload:
        s.icon = payload.get("icon")
        changed = True
    if "caddy_managed" in payload:
        s.caddy_managed = bool(payload.get("caddy_managed"))
        changed = True
    if changed:
        sess.add(s)
        sess.commit()
    return JSONResponse(content={"ok": True, "service": s.dict()})

@app.post("/api/caddy/apply")
async def caddy_apply():
    if not app.state.caddy:
        return {"ok": False, "error": "Caddy integration disabled"}
    sess = get_session()
    services = list_services()
    results = {}
    for s in services:
        route_id = str(s.id)
        hostname = s.hostname
        upstream = f"{s.scheme or 'http'}://{s.host}:{s.port}"
        ok = await app.state.caddy.create_route(route_id, hostname, upstream)
        results[hostname] = ok
        if ok:
            s.caddy_managed = True
            sess.add(s)
            sess.commit()
    return {"ok": True, "results": results}

async def _caddy_autosync_loop():
    """Background loop that ensures discovered services are applied to Caddy when available.

    This loop is conservative: it only attempts to create routes for services where
    caddy_managed is False and last_seen is recent. It sleeps between cycles and
    logs results. The interval is configurable by LOCALDECK_CADDY_AUTOSYNC_INTERVAL.
    """
    while True:
        try:
            sess = get_session()
            services = list_services()
            for s in services:
                try:
                    # only attempt to apply for services that are not yet managed
                    if s.caddy_managed:
                        continue
                    # only apply to services seen within the last 15 minutes
                    from datetime import datetime, timedelta
                    if s.last_seen and (datetime.utcnow() - s.last_seen) > timedelta(minutes=15):
                        continue
                    route_id = str(s.id)
                    hostname = s.hostname
                    upstream = f"{s.scheme or 'http'}://{s.host}:{s.port}"
                    ok = await app.state.caddy.create_route(route_id, hostname, upstream)
                    if ok:
                        s.caddy_managed = True
                        sess.add(s)
                        sess.commit()
                except Exception:
                    logger.exception("error applying caddy route for service %s", s.id)
        except Exception:
            logger.exception("caddy autosync loop failed")
        await asyncio.sleep(CADDY_AUTOSYNC_INTERVAL)
