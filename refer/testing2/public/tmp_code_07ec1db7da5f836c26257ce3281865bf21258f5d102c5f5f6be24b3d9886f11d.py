# Save the pytest script to test_login.py
with open("test_login.py", "w") as f:
    f.write("""
import pytest

# Mock login function to simulate the login process
def login(username, password):
    if username == "valid_user" and password == "valid_password":
        return {"status": "success", "message": "Login successful"}
    elif username == "valid_user" and password != "valid_password":
        return {"status": "failure", "message": "Invalid password"}
    elif not username:
        return {"status": "failure", "message": "Username is required"}
    elif not password:
        return {"status": "failure", "message": "Password is required"}
    else:
        return {"status": "failure", "message": "Invalid username"}

# Test case for valid login
def test_valid_login():
    result = login("valid_user", "valid_password")
    assert result["status"] == "success"
    assert result["message"] == "Login successful"

# Test case for invalid password
def test_invalid_password():
    result = login("valid_user", "wrong_password")
    assert result["status"] == "failure"
    assert result["message"] == "Invalid password"

# Test case for missing username
def test_missing_username():
    result = login("", "valid_password")
    assert result["status"] == "failure"
    assert result["message"] == "Username is required"

# Test case for missing password
def test_missing_password():
    result = login("valid_user", "")
    assert result["status"] == "failure"
    assert result["message"] == "Password is required"

# Test case for invalid username
def test_invalid_username():
    result = login("invalid_user", "valid_password")
    assert result["status"] == "failure"
    assert result["message"] == "Invalid username"

if __name__ == "__main__":
    pytest.main()
""")

# Run the pytest script
import subprocess
subprocess.run(["pytest", "test_login.py"])
