"""Gerçek HTTP doğrulaması ve geçici yapılandırma dosyasıyla F58 testleri."""

import copy
import json
import stat
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import src.web.app as module

TOKEN = "fictional-omc-owner-only-token-for-tests-20261011"
KEY = "fictional-provider-key-do-not-use-live-ABCD"


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("OMC_API_TOKEN", TOKEN)
    monkeypatch.delenv("OMC_SETTINGS_ORIGIN", raising=False)
    monkeypatch.setattr(module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(module, "SETTINGS_FILE", tmp_path / "config.json")
    data = {
        "models": {
            "deepseek": {"api_key": KEY, "base_url": "https://provider.invalid/v1"},
            "short": {"api_key": "abc"},
            "custom_fixture": {
                "api_key": KEY,
                "base_url": "https://custom.invalid/v1",
                "model_id": "fictional-model",
            },
        },
        "defaults": {"model": "deepseek"},
    }
    module.SETTINGS_FILE.write_text(json.dumps(data))
    return data


@pytest.fixture
def owner(settings):
    with TestClient(module.app, headers={"Authorization": "Bearer " + TOKEN}) as client:
        yield client


@pytest.mark.parametrize("method,path", [
    ("GET", "/"), ("GET", "/history"), ("GET", "/dashboard"),
    ("GET", "/api/tasks"), ("GET", "/api/tasks/fictional"), ("GET", "/api/history"),
    ("GET", "/api/config"), ("GET", "/api/sessions"),
    ("GET", "/api/share"), ("GET", "/sse/execute/fictional"),
    ("POST", "/api/execute"), ("POST", "/api/chat"),
    ("POST", "/api/share"), ("POST", "/api/share/abcd1234/import"),
    ("DELETE", "/api/share/abcd1234"),
    ("DELETE", "/api/tasks/fictional"), ("DELETE", "/api/history/fictional"),
])
@pytest.mark.parametrize("authorization", [None, "Bearer fictional-team-member"])
def test_private_web_and_actions_require_owner(settings, method, path, authorization):
    with TestClient(module.app) as client, patch("fastapi.BackgroundTasks.add_task") as enqueue:
        response = client.request(method, path, headers={
            **({"Authorization": authorization} if authorization else {}),
            "omc_owner_authenticated": "true",  # HTTP başlığı scope işaretini taklit edemez.
        }, json={"task": "fictional dry-run task", "project_path": "."} if method == "POST" else None)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    enqueue.assert_not_called()


def test_browser_basic_owner_can_read_and_delete_tasks(settings, monkeypatch):
    import src.web.history_api as history
    manager = module.TaskManager()
    task_id = manager.create_task(task_desc="fictional-private-owner-task")
    monkeypatch.setattr(module, "task_manager", manager)
    monkeypatch.setattr(history, "API_TOKEN", "fictional-stale-import-token")
    with TestClient(module.app) as client:
        assert client.get("/", auth=("yonetici", TOKEN)).status_code == 200
        listing = client.get("/api/tasks", auth=("yonetici", TOKEN))
        assert listing.status_code == 200
        assert listing.json()["tasks"][0]["task_id"] == task_id
        assert listing.headers["cache-control"] == "no-store"
        private = client.get("/api/tasks/" + task_id, auth=("yonetici", TOKEN))
        assert private.status_code == 200
        assert private.json()["task"] == "fictional-private-owner-task"
        assert private.headers["cache-control"] == "no-store"
        assert client.delete("/api/tasks/" + task_id, auth=("yonetici", TOKEN)).status_code == 200
    assert manager.get_task(task_id) is None


@pytest.mark.parametrize("basic", [True, False])
def test_owner_can_delete_history_independent_of_import_token(settings, monkeypatch, tmp_path, basic):
    import src.web.history_api as history
    store = history.HistoryStore(tmp_path / "fictional-history")
    store.save("fixture", {"task": "fictional-private-record"})
    monkeypatch.setattr(history, "history_store", store)
    monkeypatch.setattr(history, "API_TOKEN", "fictional-stale-import-token")
    with TestClient(module.app) as client:
        response = client.delete("/api/history/fixture",
                                 auth=("yonetici", TOKEN) if basic else None,
                                 headers={} if basic else {"Authorization": "Bearer " + TOKEN})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert store.load("fixture") is None


def test_foreign_origin_cannot_queue_execution(owner):
    with patch("fastapi.BackgroundTasks.add_task") as enqueue:
        assert owner.post("/api/execute", headers={"Origin": "https://attacker.invalid"},
                          json={"task": "fictional dry-run task", "project_path": "."}).status_code == 403
    enqueue.assert_not_called()


def test_owner_key_rotation_also_revokes_private_pages(owner, monkeypatch):
    monkeypatch.setenv("OMC_API_TOKEN", "fictional-new-owner-token-for-tests-20261011")
    assert owner.get("/").status_code == 401
    assert owner.get("/api/tasks").status_code == 401


@pytest.mark.parametrize("path", ["/health", "/favicon.ico", "/manifest.webmanifest", "/sw.js"])
def test_public_operational_assets_remain_accessible(settings, path):
    with TestClient(module.app) as client:
        assert client.get(path).status_code == 200


def test_published_share_read_only_and_expiry(settings, monkeypatch, tmp_path):
    import src.web.share_api as share
    monkeypatch.setattr(share, "SHARE_DIR", tmp_path)
    record = {"share_id": "abcd1234", "created_at": "2026-10-11T00:00:00",
              "session": {"history": {"task": "fictional-explicitly-published-content"}}}
    target = tmp_path / "share_abcd1234.json"
    target.write_text(json.dumps(record))
    with TestClient(module.app) as client:
        response = client.get("/api/share/abcd1234")
        assert response.status_code == 200
        assert "fictional-explicitly-published-content" in response.text
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/share").status_code == 401
        assert client.delete("/api/share/abcd1234").status_code == 401
        record["expires_at"] = "2000-01-01T00:00:00"
        target.write_text(json.dumps(record))
        assert client.get("/api/share/abcd1234").status_code == 410


@pytest.mark.parametrize("path,method", [
    ("/settings", "get"), ("/api/settings", "get"),
    ("/api/settings", "post"), ("/api/test-connection", "post"),
])
@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "Bearer fictional-team-member"])
def test_anonymous_and_non_admin_cannot_access(settings, path, method, authorization):
    before = module.SETTINGS_FILE.read_bytes()
    with TestClient(module.app) as client, patch("httpx.Client") as outbound:
        response = client.request(method, path, headers={"Authorization": authorization} if authorization else {},
                                  json={"models": {"deepseek": {"api_key": "changed"}}} if method == "post" else None)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic ")
    assert response.headers["cache-control"] == "no-store"
    assert module.SETTINGS_FILE.read_bytes() == before
    outbound.assert_not_called()


@pytest.mark.parametrize("token", [None, "", "short", " " * 40])
def test_missing_or_weak_token_prevents_startup(settings, monkeypatch, token):
    if token is None:
        monkeypatch.delenv("OMC_API_TOKEN")
    else:
        monkeypatch.setenv("OMC_API_TOKEN", token)
    with pytest.raises(RuntimeError, match="OMC_API_TOKEN"):
        with TestClient(module.app):
            pass
    # Yaşam döngüsü çalıştırılmadan da API kapalı kalır.
    assert TestClient(module.app).get("/api/settings").status_code == 503


def test_basic_owner_and_wrong_username(settings):
    with TestClient(module.app) as client:
        response = client.get("/settings", auth=("yonetici", TOKEN))
        assert response.status_code == 200
        assert KEY not in response.text and TOKEN not in response.text
        assert client.get("/api/settings", auth=("uye", TOKEN)).status_code == 401
        assert client.get("/api/settings", headers={"Authorization": "Basic !!!"}).status_code == 401


def test_response_removes_keys_without_mutating_disk_or_source(owner, settings):
    original = copy.deepcopy(settings)
    before = module.SETTINGS_FILE.read_bytes()
    with patch.object(module, "_read_settings", return_value=settings):
        response = owner.get("/api/settings")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert KEY not in response.text
    assert settings == original
    assert module.SETTINGS_FILE.read_bytes() == before
    for model in response.json()["models"].values():
        assert "api_key" not in model
        assert model["has_key"] is True
    assert response.json()["models"]["short"]["api_key_masked"] == "****"


@pytest.mark.parametrize("origin", ["https://attacker.invalid", "null", "https://testserver:444"])
def test_foreign_origin_cannot_write(owner, origin):
    before = module.SETTINGS_FILE.read_bytes()
    response = owner.post("/api/settings", headers={"Origin": origin}, json={"models": {"deepseek": {"api_key": "changed"}}})
    assert response.status_code == 403
    assert module.SETTINGS_FILE.read_bytes() == before


@pytest.mark.parametrize("origin", ["http://testserver", "https://testserver"])
def test_same_origin_works_behind_tls_proxy(owner, origin, monkeypatch):
    if origin.startswith("https:"):
        monkeypatch.setenv("OMC_SETTINGS_ORIGIN", origin)
    assert owner.post("/api/settings", headers={"Origin": origin}, json={"defaults": {"timeout": 60}}).status_code == 200


def test_public_origin_rejects_http_downgrade(owner, monkeypatch):
    monkeypatch.setenv("OMC_SETTINGS_ORIGIN", "https://testserver")
    before = module.SETTINGS_FILE.read_bytes()
    assert owner.post("/api/settings", headers={"Origin": "http://testserver"}, json={"defaults": {"timeout": 90}}).status_code == 403
    assert module.SETTINGS_FILE.read_bytes() == before


@pytest.mark.parametrize("origin", ["null", "https://bad host", "https://testserver/path", "https://@testserver", "https://testserver?x=1"])
def test_invalid_public_origin_prevents_startup(settings, monkeypatch, origin):
    monkeypatch.setenv("OMC_SETTINGS_ORIGIN", origin)
    with pytest.raises(RuntimeError, match="OMC_SETTINGS_ORIGIN"):
        with TestClient(module.app):
            pass


def test_key_preservation_replacement_clear_and_file_permissions(owner):
    assert owner.post("/api/settings", json={"models": {"deepseek": {"base_url": "https://new.invalid", "has_key": False, "api_key_masked": "***"}}}).status_code == 200
    assert module._read_settings()["models"]["deepseek"]["api_key"] == KEY
    assert owner.post("/api/settings", json={"models": {"deepseek": {"api_key": "*****ABCD"}}}).status_code == 200
    assert module._read_settings()["models"]["deepseek"]["api_key"] == KEY
    assert owner.post("/api/settings", json={"models": {"deepseek": {"api_key": "fictional-replacement"}}}).status_code == 200
    assert module._read_settings()["models"]["deepseek"]["api_key"] == "fictional-replacement"
    assert stat.S_IMODE(module.SETTINGS_FILE.stat().st_mode) == 0o600
    assert "has_key" not in module._read_settings()["models"]["deepseek"]
    assert owner.post("/api/settings", json={"models": {"deepseek": {"api_key": ""}}}).status_code == 200
    assert module._read_settings()["models"]["deepseek"]["api_key"] == ""


@pytest.mark.parametrize("payload", [
    {"models": []}, {"defaults": []}, {"models": {"deepseek": []}},
    {"models": {"deepseek": {"api_key": None}}},
])
def test_invalid_update_preserves_file(owner, payload):
    before = module.SETTINGS_FILE.read_bytes()
    assert owner.post("/api/settings", json=payload).status_code == 422
    assert module.SETTINGS_FILE.read_bytes() == before


def test_atomic_write_failure_preserves_existing_file(owner):
    before = module.SETTINGS_FILE.read_bytes()
    with patch.object(module.os, "replace", side_effect=OSError("fictional disk failure")):
        with pytest.raises(OSError):
            owner.post("/api/settings", json={"defaults": {"timeout": 90}})
    assert module.SETTINGS_FILE.read_bytes() == before
    assert list(module.SETTINGS_DIR.iterdir()) == [module.SETTINGS_FILE]


def test_token_rotation_revokes_old_basic_and_bearer(owner, monkeypatch):
    replacement = "fictional-replacement-owner-token-for-tests-20261011"
    monkeypatch.setenv("OMC_API_TOKEN", replacement)
    assert owner.get("/api/settings").status_code == 401
    assert owner.get("/api/settings", auth=("yonetici", TOKEN)).status_code == 401
    assert owner.get("/api/settings", headers={"Authorization": "Bearer " + replacement}).status_code == 200


@pytest.mark.parametrize("payload,url,model_id", [
    ({"provider": "deepseek", "api_key": "", "base_url": "https://attacker.invalid"}, "https://provider.invalid/v1/chat/completions", "deepseek-chat"),
    ({"model_name": "custom_fixture", "api_key": "", "base_url": "https://attacker.invalid", "model_id": "other"}, "https://custom.invalid/v1/chat/completions", "fictional-model"),
])
def test_saved_key_test_uses_saved_target_without_returning_key(owner, payload, url, model_id):
    response = MagicMock(status_code=200, headers={"content-type": "application/json"})
    with patch("httpx.Client") as provider:
        outbound = provider.return_value.__enter__.return_value
        outbound.post.return_value = response
        result = owner.post("/api/test-connection", json=payload)
    assert result.status_code == 200 and result.json()["ok"] is True
    assert KEY not in result.text
    assert outbound.post.call_args.args == (url,)
    assert outbound.post.call_args.kwargs["headers"]["Authorization"] == "Bearer " + KEY
    assert outbound.post.call_args.kwargs["json"]["model"] == model_id


def test_unsaved_key_has_no_outbound_call(owner):
    with patch("httpx.Client") as outbound:
        result = owner.post("/api/test-connection", json={"provider": "glm"})
    assert result.status_code == 400
    outbound.assert_not_called()


@pytest.mark.parametrize("error_kind", ["response", "exception"])
def test_provider_error_cannot_echo_saved_key(owner, error_kind):
    response = MagicMock(status_code=500)
    response.json.return_value = {"error": {"message": "rejected " + KEY}}
    with patch("httpx.Client") as provider:
        outbound = provider.return_value.__enter__.return_value
        if error_kind == "exception":
            outbound.post.side_effect = RuntimeError("failed " + KEY)
        else:
            outbound.post.return_value = response
        result = owner.post("/api/test-connection", json={"provider": "deepseek"})
    assert result.status_code in (500, 502)
    assert KEY not in result.text
    assert "[gizlendi]" in result.json()["msg"]
