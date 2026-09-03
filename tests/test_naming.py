import pytest
from localdeck.naming import slugify

def test_slugify():
    assert slugify("Grafana") == "grafana"
    assert slugify("My Admin Console") == "my-admin-console"
    assert slugify("---") == "service"
