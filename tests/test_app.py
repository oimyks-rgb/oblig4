def test_blueprints_registered(app):
    assert {"shop", "account", "admin"} <= set(app.blueprints)


def test_public_pages_load(client):
    for url in ("/", "/account/login"):
        assert client.get(url).status_code == 200, url


def test_account_and_admin_require_login(client):
    for url in ("/account/", "/admin/", "/admin/food-items/"):
        response = client.get(url)
        assert response.status_code == 302, url
        assert "/account/login" in response.headers["Location"]
