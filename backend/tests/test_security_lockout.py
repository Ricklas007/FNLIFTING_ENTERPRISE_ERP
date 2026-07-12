from tests.enterprise_test_utils import client


def test_login_lockout_after_repeated_failures():
    api = client()
    for _ in range(5):
        failed = api.post("/api/v1/auth/login", json={"identifier": "lockout.qa@fnlifting.com", "password": "WrongPass123", "portal": "staff"})
        assert failed.status_code == 401
    locked = api.post("/api/v1/auth/login", json={"identifier": "lockout.qa@fnlifting.com", "password": "WrongPass123", "portal": "staff"})
    assert locked.status_code == 429
    api.close()
