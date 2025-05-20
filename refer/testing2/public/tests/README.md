# API Test Automation

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the tests:
   ```bash
   ./run_tests.sh
   ```

## Test Structure
- `conftest.py`: Configuration and fixtures
- `test_auth_register.py`: Tests for user registration
- `test_auth_login.py`: Tests for user login
- `test_products.py`: Tests for product management
- `test_cart.py`: Tests for cart management
- `test_orders.py`: Tests for order management

## Reporting
Test results are generated using Allure. After running the tests, the report will be automatically opened in your default web browser.