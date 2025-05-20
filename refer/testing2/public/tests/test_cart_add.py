import allure
import pytest

@allure.feature("Cart Management")
class TestCartAPI:
    @allure.story("Add to Cart")
    @pytest.mark.parametrize("test_id, headers, payload, expected_status", [
        ("TC013", {"authorization": "valid_token"}, {"product_id": 1, "quantity": 1}, 200),
        ("TC014", {"authorization": "valid_token"}, {"product_id": 1, "quantity": 0}, 422),
        ("TC015", {"authorization": "invalid_token"}, {"product_id": 1, "quantity": 1}, 401),
    ])
    def test_add_to_cart(self, api_client, test_id, headers, payload, expected_status):
        with allure.step(f"Test Case {test_id}: Add to cart with payload {payload}"):
            response = api_client.post("/cart/add", headers=headers, json=payload)
            assert response.status_code == expected_status
            if expected_status == 200:
                assert "cart_id" in response.json()