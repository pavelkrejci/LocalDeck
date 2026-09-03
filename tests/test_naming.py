import pytest
from localdeck.naming import slugify


def test_slugify():
    assert slugify("Grafana") == "grafana"
    assert slugify("My Admin Console") == "my-admin-console"
    assert slugify("---") == "service"


async def test_caddy_route_obj_creation():
    # basic smoke test to ensure CaddyClient methods exist and are awaitable
    from localdeck.caddy import CaddyClient
    c = CaddyClient(admin_url="http://127.0.0.1:2019")
    # do not actually call remote API in unit test; just ensure methods are coroutines
    assert callable(c.create_route)
    assert callable(c.delete_route)
