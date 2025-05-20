import allure
import pytest

@allure.feature("Order Management")
class TestOrderAPI:

    @allure.story("Create Order")
    @pytest.mark.parametrize("test_id, order_data, expected", [
        ("TC011", {"address_id": 1}, 200),
        ("TC012", {"address_id": "invalid"}, 422)
    ])
    def test_create_order(self, api_client, auth_token, test_id, order_data, expected):
        with allure.step(f"Test Case {test_id}: Create new order"):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = api_client("POST", "/orders/create", json=order_data, headers=headers)
            assert response.status_code == expected