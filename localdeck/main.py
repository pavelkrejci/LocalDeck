from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from jinja2 import Environment, PackageLoader, select_autoescape
import asyncio
import logging
import os
from .discovery import Scanner
from .models import init_db, get_session, Service, list_services
from .caddy import CaddyClient

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

@app.on_event("startup")
async def startup_event():
    init_db()
    scanner = Scanner()
    # store on app state so CLI or tests can access
    app.state.scanner = scanner
    # caddy client
    app.state.caddy = CaddyClient(admin_url=CADDY_ADMIN) if CADDY_ENABLED else None
    asyncio.create_task(scanner.run_background())

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

# simple endpoint to trigger applying Caddy routes for all services (manual)
@app.post("/api/caddy/apply")
async def caddy_apply():
    if not app.state.caddy:
        return {"ok": False, "error": "Caddy integration disabled"}
    sess = get_session()
    services = sess.exec(select(Service)).all() if False else list_services()
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
