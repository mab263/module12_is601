import pytest


@pytest.mark.parametrize("url", ["/docs", "/redoc", "/openapi.json"])
def test_documentation_pages_are_served(api_client, url):
    assert api_client.get(url).status_code == 200


@pytest.mark.parametrize("path", ["/users/register", "/users/login"])
def test_user_endpoints_appear_in_the_openapi_schema(api_client, path):
    paths = api_client.get("/openapi.json").json()["paths"]
    assert "post" in paths[path]