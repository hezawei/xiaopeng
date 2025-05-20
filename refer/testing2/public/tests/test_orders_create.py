import allure
import pytest

@allure.feature("Order Management")
class TestOrderAPI:
    @allure.story("Create Order")
    @pytest.mark.parametrize("test_id, headers, payload, expected_status", [
        ("TC016", {"authorization": "valid_token"}, {"address_id": 1}, 200),
        ("TC017", {"authorization": "valid_token"}, {"address_id": 0}, 422),
        ("TC018", {"authorization": "invalid_token"}, {"address_id": 1}, 401),
    ])
    def test_create_order(self, api_client, test_id, headers, payload, expected_status):
        with allure.step(f"Test Case {test_id}: Create order with payload {payload}"):
            response = api_client.post("/orders/create", headers=headers, json=payload)
            assert response.status_code == expected_status
            if expected_status == 200:
                assert "order_id" in response.json()