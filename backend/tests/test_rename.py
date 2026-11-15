"""The caregiver can change the elder's name; the elder link stays the same."""

from fastapi.testclient import TestClient

from app.main import app


def test_rename_keeps_the_link():
    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"elder_name": "Ajji"}).json()
        renamed = client.patch(f"/api/profiles/{created['id']}", json={"elder_name": "  Elder  "})
        assert renamed.status_code == 200 and renamed.json()["elder_name"] == "Elder"
        profile = client.get(f"/api/profiles/{created['id']}").json()["profile"]
        assert profile["elder_name"] == "Elder" and profile["share_token"] == created["share_token"]
        assert client.patch(f"/api/profiles/{created['id']}", json={"elder_name": "   "}).status_code == 422
        assert client.patch("/api/profiles/99999", json={"elder_name": "X"}).status_code == 404
