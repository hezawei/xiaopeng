import pytest
import requests
import allure
import logging
from typing import Dict, Any

# 基础URL
BASE_URL = "http://localhost:8001"

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试数据
TEST_USER = {
    "username": "testuser",
    "password": "testpassword",
    "email": "testuser@example.com",
    "phone": "1234567890"
}

TEST_PRODUCT = {
    "name": "Test Product",
    "price": 19.99,
    "category": "Test Category"
}

TEST_CART_ITEM = {
    "product_id": 1,
    "quantity": 2
}

TEST_ORDER = {
    "address_id": 1
}

# Fixtures

@pytest.fixture(scope="session")
def register_user():
    """注册用户并返回用户信息"""
    with allure.step("注册新用户"):
        response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        allure.attach("Request", str(response.request.body), allure.attachment_type.TEXT)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 201
        return TEST_USER

@pytest.fixture(scope="session")
def login_user(register_user):
    """登录用户并返回JWT token"""
    with allure.step("用户登录"):
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": register_user["username"],
            "password": register_user["password"]
        })
        allure.attach("Request", str(response.request.body), allure.attachment_type.TEXT)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 200
        token = response.json().get("access_token")
        assert token is not None
        return token

@pytest.fixture(scope="session")
def auth_header(login_user):
    """返回带有JWT token的认证头"""
    return {"Authorization": f"Bearer {login_user}"}

# 测试用例

@allure.feature("身份验证")
@allure.story("用户注册")
@allure.severity(allure.severity_level.CRITICAL)
def test_register_user(register_user):
    """测试用户注册功能"""
    with allure.step("验证注册用户信息"):
        assert register_user["username"] == TEST_USER["username"]
        assert register_user["email"] == TEST_USER["email"]

@allure.feature("身份验证")
@allure.story("用户登录")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_user(login_user):
    """测试用户登录功能"""
    with allure.step("验证登录返回的token"):
        assert login_user is not None

@allure.feature("产品管理")
@allure.story("获取产品列表")
@allure.severity(allure.severity_level.NORMAL)
def test_get_products():
    """测试获取产品列表功能"""
    with allure.step("获取产品列表"):
        response = requests.get(f"{BASE_URL}/products")
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 200
        products = response.json()
        assert isinstance(products, list)

@allure.feature("购物车管理")
@allure.story("获取购物车内容")
@allure.severity(allure.severity_level.NORMAL)
def test_get_cart(auth_header):
    """测试获取购物车内容功能"""
    with allure.step("获取购物车内容"):
        response = requests.get(f"{BASE_URL}/cart", headers=auth_header)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 200
        cart = response.json()
        assert isinstance(cart, dict)

@allure.feature("购物车管理")
@allure.story("添加商品到购物车")
@allure.severity(allure.severity_level.NORMAL)
def test_add_to_cart(auth_header):
    """测试添加商品到购物车功能"""
    with allure.step("添加商品到购物车"):
        response = requests.post(f"{BASE_URL}/cart/add", headers=auth_header, json=TEST_CART_ITEM)
        allure.attach("Request", str(response.request.body), allure.attachment_type.TEXT)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 200
        result = response.json()
        assert result.get("success") is True

@allure.feature("订单管理")
@allure.story("创建订单")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_order(auth_header):
    """测试创建订单功能"""
    with allure.step("创建订单"):
        response = requests.post(f"{BASE_URL}/orders/create", headers=auth_header, json=TEST_ORDER)
        allure.attach("Request", str(response.request.body), allure.attachment_type.TEXT)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 201
        order = response.json()
        assert order.get("id") is not None

# 错误处理和异常场景

@allure.feature("身份验证")
@allure.story("用户注册 - 重复用户")
@allure.severity(allure.severity_level.NORMAL)
def test_register_duplicate_user(register_user):
    """测试注册重复用户时的错误处理"""
    with allure.step("尝试注册重复用户"):
        response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        allure.attach("Request", str(response.request.body), allure.attachment_type.TEXT)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 400
        error = response.json()
        assert error.get("error") == "User already exists"

@allure.feature("身份验证")
@allure.story("用户登录 - 错误凭据")
@allure.severity(allure.severity_level.NORMAL)
def test_login_invalid_credentials(register_user):
    """测试使用错误凭据登录时的错误处理"""
    with allure.step("使用错误密码登录"):
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": register_user["username"],
            "password": "wrongpassword"
        })
        allure.attach("Request", str(response.request.body), allure.attachment_type.TEXT)
        allure.attach("Response", response.text, allure.attachment_type.TEXT)
        assert response.status_code == 401
        error = response.json()
        assert error.get("error") == "Invalid credentials"

# 自定义报告标题和样式

def pytest_html_report_title(report):
    report.title = "API自动化测试报告"

def pytest_html_results_summary(prefix, summary, postfix):
    prefix.extend([f"<h2>测试环境: {BASE_URL}</h2>"])
    postfix.extend([f"<p>测试完成时间: {summary['duration']}</p>"])

# 测试结束时的额外信息

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == 'call':
        if report.failed:
            allure.attach("失败截图", "截图内容", allure.attachment_type.PNG)