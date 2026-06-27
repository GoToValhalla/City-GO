from fastapi.testclient import TestClient

from main import app


@app.get("/__test__/admin-error-contract")
def _admin_error_contract_route() -> None:
    raise RuntimeError("contract boom")


def test_unhandled_error_returns_json_with_request_id_new() -> None:
    response = TestClient(app).get("/__test__/admin-error-contract", headers={"X-Request-ID": "req-contract"})

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-contract"
    body = response.json()
    assert body["request_id"] == "req-contract"
    assert body["path"] == "/__test__/admin-error-contract"
    assert body["error"] == "unhandled_request_exception"
