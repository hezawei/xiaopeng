import allure
import pytest

@allure.feature("Cart Management")
class TestCartAPI:

    @allure.story("Get Cart")
    def test_get_cart(self, api_client, auth_token):
        with allure.step("Test get cart with valid token"):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = api_client("GET", "/cart", headers=headers)
            assert response.status_code == 200
            assert isinstance(response.json(), dict)

    @allure.story("Add to Cart")
    @pytest.mark.parametrize("test_id, item_data, expected", [
        ("TC009", {"product_id": 1, "quantity": 2}, 200),
        ("TC010", {"product_id": "invalid", "quantity": 0}, 422)
    ])
    def test_add_to_cart(self, api_client, auth_token, test_id, item_data, expected):
        with allure.step(f"Test Case {test_id}: Add item to cart"):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = api_client("POST", "/cart/add", json=item_data, headers=headers)
            assert response.status_code == expected