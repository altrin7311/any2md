"""HTTP serve-mode tests — FastAPI TestClient, fake converter, no real conversions."""

from pathlib import Path

from fastapi.testclient import TestClient

from any2md.queue import JobQueue
from any2md.server import create_app


def _make_convert(tmp_path):
    def _fake_convert(target, output_dir, provider, on_event):
        path = Path(tmp_path) / "result.md"
        path.write_text(f"# converted {target}\n")
        return path

    return _fake_convert


def _client(tmp_path, token=None):
    queue = JobQueue(convert_fn=_make_convert(tmp_path), workers=1)
    app = create_app(queue=queue, token=token, output_dir=str(tmp_path))
    # `with` keeps the portal event loop alive so queue workers persist across requests.
    return TestClient(app)


def test_convert_returns_job_id(tmp_path):
    with _client(tmp_path) as client:
        resp = client.post("/convert", json={"target": "https://example.com/x"})
        assert resp.status_code == 200
        assert "id" in resp.json()


def test_job_status_reports_state(tmp_path):
    with _client(tmp_path) as client:
        jid = client.post("/convert", json={"target": "https://example.com/x"}).json()["id"]
        resp = client.get(f"/jobs/{jid}")
        assert resp.status_code == 200
        assert resp.json()["status"] in (
            "queued",
            "extracting",
            "enriching",
            "writing",
            "done",
        )


def test_download_returns_markdown(tmp_path):
    with _client(tmp_path) as client:
        jid = client.post("/convert", json={"target": "https://example.com/x"}).json()["id"]
        resp = client.get(f"/jobs/{jid}/download")
        assert resp.status_code == 200
        assert "# converted" in resp.text


def test_unknown_job_returns_404(tmp_path):
    with _client(tmp_path) as client:
        assert client.get("/jobs/deadbeef").status_code == 404


def test_auth_open_when_no_token(tmp_path):
    with _client(tmp_path, token=None) as client:
        resp = client.post("/convert", json={"target": "https://example.com/x"})
        assert resp.status_code == 200


def test_auth_rejects_missing_token(tmp_path):
    with _client(tmp_path, token="secret") as client:
        resp = client.post("/convert", json={"target": "https://example.com/x"})
        assert resp.status_code == 401


def test_auth_accepts_correct_token(tmp_path):
    with _client(tmp_path, token="secret") as client:
        resp = client.post(
            "/convert",
            json={"target": "https://example.com/x"},
            headers={"Authorization": "Bearer secret"},
        )
        assert resp.status_code == 200
