"""Тесты REST API админки."""

from app import app


def test_stats_and_status_patch():
    client = app.test_client()
    assert client.get("/api/stats").status_code == 200
    leads = client.get("/api/leads").get_json()
    if not leads:
        return
    lead_id = leads[-1]["id"]
    resp = client.patch(f"/api/leads/{lead_id}/status", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "in_progress"
    bad = client.patch(f"/api/leads/{lead_id}/status", json={"status": "hack"})
    assert bad.status_code == 400
