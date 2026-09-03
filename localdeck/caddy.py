import httpx
import logging
from typing import Optional

logger = logging.getLogger("localdeck.caddy")

class CaddyClient:
    def __init__(self, admin_url: str = "http://127.0.0.1:2019", timeout: float = 3.0):
        self.admin_url = admin_url.rstrip("/")
        self.timeout = timeout

    async def create_route(self, route_id: str, hostname: str, upstream: str) -> bool:
        """Create or replace a server config for a single-host route managed by LocalDeck.

        This implementation is conservative: it creates a dedicated server named
        localdeck_{route_id} with a single route matching the hostname and a reverse_proxy
        handler to the upstream. It will only attempt the operation and log detailed
        errors if the Caddy Admin API is unavailable. The caller must ensure the
        admin_url is trusted and available.
        """
        # upstream expected like http://127.0.0.1:3000 or https://127.0.0.1:8443
        dial = upstream.replace("http://", "").replace("https://", "")
        server_name = f"localdeck_{route_id}"
        server_obj = {
            "listen": ["127.0.0.1:80"],
            "routes": [
                {
                    "match": [{"host": [hostname.replace(':', '')]}],
                    "handle": [
                        {
                            "handler": "reverse_proxy",
                            "upstreams": [{"dial": dial}],
                        }
                    ],
                    "terminal": True,
                }
            ],
        }
        url = f"{self.admin_url}/config/apps/http/servers/{server_name}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.put(url, json=server_obj)
                if r.status_code in (200, 201, 204):
                    logger.info("Caddy: created/updated route %s -> %s", hostname, upstream)
                    return True
                else:
                    logger.warning("Caddy: unexpected status %s when creating route: %s", r.status_code, r.text)
                    return False
        except Exception as e:
            logger.debug("Caddy: failed to create route: %s", e, exc_info=True)
            return False

    async def delete_route(self, route_id: str) -> bool:
        server_name = f"localdeck_{route_id}"
        url = f"{self.admin_url}/config/apps/http/servers/{server_name}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.delete(url)
                if r.status_code in (200, 204):
                    logger.info("Caddy: deleted route %s", server_name)
                    return True
                else:
                    logger.warning("Caddy: unexpected status %s when deleting route: %s", r.status_code, r.text)
                    return False
        except Exception as e:
            logger.debug("Caddy: failed to delete route: %s", e, exc_info=True)
            return False
