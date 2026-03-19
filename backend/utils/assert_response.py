
# for test
def assert_error_response(resp, status_code, code, info=None):
    """统一的错误响应断言"""
    assert resp.status_code == status_code, f"Expected status_code={status_code}, got {resp.status_code}"
    data = resp.json()
    assert data["code"] == code, f"Expected code={code}, got {data['code']}"
    if info:
        assert info == data["info"], f"Expected info='{info}', got '{data['info']}'"
