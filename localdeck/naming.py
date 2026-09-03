import re
from .models import get_session, Service

def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    if not s:
        s = "service"
    return s

def generate_hostname_for(service: Service) -> str:
    base = None
    if service.title:
        base = slugify(service.title)
    else:
        base = f"service-{service.port}"
    sess = get_session()
    existing = sess.exec(Service.select()).all() if False else sess.exec(
        "SELECT name FROM Service WHERE name IS NOT NULL"
    ).all()
    # fallback: simple uniqueness by querying names
    names = [r[0] for r in existing if r[0]]
    candidate = base
    suffix = 1
    while candidate in names:
        suffix += 1
        candidate = f"{base}-{suffix}"
    return f"{candidate}.localhost"
