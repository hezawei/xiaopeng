import pytest
import requests
from typing import Dict, Any

@pytest.fixture(scope="session")
def api_client():
    base_url = "http://localhost:8000"  # 根据实际环境配置
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    def _client(method: str, endpoint: str, **kwargs):
        url = f"{base_url}{endpoint}"
        return requests.request(method, url, headers=headers, **kwargs)
    
    return _client

@pytest.fixture
def auth_token(api_client):
    # 获取认证token的fixture
    login_data = {
        "username": "testuser",
        "password": "testpass"
    }
    response = api_client("POST", "/auth/login", json=login_data)
    return response.json().get("access_token")