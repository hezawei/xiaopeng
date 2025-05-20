import allure
import pytest

@allure.feature("Authentication")
class TestAuthLoginAPI:
    
    @allure.story("User Login")
    @pytest.mark.parametrize("test_id, credentials, expected", [
        ("TC003", {"username": "testuser", "password": "testpass"}, 200),
        ("TC004", {"username": "wronguser", "password": "wrongpass"}, 401),
        ("TC005", {"username": "", "password": ""}, 422)
    ])
    def test_user_login(self, api_client, test_id, credentials, expected):
        with allure.step(f"Test Case {test_id}: User login"):
            response = api_client("POST", "/auth/login", json=credentials)
            assert response.status_code == expected
            if expected == 200:
                assert "access_token" in response.json()