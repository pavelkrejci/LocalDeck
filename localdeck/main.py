from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from jinja2 import Environment, PackageLoader, select_autoescape
import asyncio
import logging
from .discovery import Scanner
from .models import init_db, get_session, Service

logger = logging.getLogger("localdeck")
app = FastAPI()

env = Environment(
    loader=PackageLoader("localdeck", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# serve favicons and other assets from localdeck/static
app.mount("/static", StaticFiles(directory="localdeck/static"), name="static")

@app.on_event("startup")
async def startup_event():
    init_db()
    scanner = Scanner()
    # store on app state so CLI or tests can access
    app.state.scanner = scanner
    asyncio.create_task(scanner.run_background())

@app.get("/")
async def index(request: Request):
    template = env.get_template("index.html")
    from .models import list_services
    services = list_services()
    html = template.render(services=services)
    return HTMLResponse(content=html)

@app.get("/api/services")
async def api_services():
    return [s.dict() for s in get_session().query(Service).all()]
