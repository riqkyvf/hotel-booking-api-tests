import allure
import pytest

from api.health import get_liveness, get_readiness


@pytest.mark.parametrize("request_health, expected_status", [
    pytest.param(get_liveness, "alive", id="live"),
    pytest.param(get_readiness, "ready", id="ready"),
])
@pytest.mark.smoke
@allure.title("Проверка состояния API возвращает 200 ({param_id})")
def test_health_returns_success(base_url, request_health, expected_status):
    response = request_health(base_url)

    assert response.status_code == 200, response.text
    assert response.headers.get("Content-Type", "").split(";")[0].strip() == "application/json"
    assert response.json() == {"status": expected_status}
