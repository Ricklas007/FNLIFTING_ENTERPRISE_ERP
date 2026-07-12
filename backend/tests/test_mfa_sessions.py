from app.security.mfa import totp_code
from tests.enterprise_test_utils import client, reset_admin_mfa


def test_mfa_setup_confirm_login_recovery_and_disable():
    reset_admin_mfa()
    api = client()
    login = api.post("/api/v1/auth/login", json={"identifier": "admin@fnlifting.com", "password": "Admin@12345", "portal": "staff"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    setup = api.post("/api/v1/enterprise/security/mfa/setup", headers=headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["qr_code_data_uri"].startswith("data:image/png;base64,")

    invalid = api.post("/api/v1/enterprise/security/mfa/confirm", headers=headers, json={"code": "000000"})
    assert invalid.status_code == 400
    confirmed = api.post("/api/v1/enterprise/security/mfa/confirm", headers=headers, json={"code": totp_code(secret)})
    assert confirmed.status_code == 200, confirmed.text
    recovery_code = confirmed.json()["recovery_codes"][0]

    challenge = api.post("/api/v1/auth/login", json={"identifier": "admin@fnlifting.com", "password": "Admin@12345", "portal": "staff"})
    assert challenge.status_code == 200
    assert challenge.json()["mfa_required"] is True
    bad_mfa = api.post("/api/v1/auth/login/mfa", json={"challenge_id": challenge.json()["challenge_id"], "code": "111111"})
    assert bad_mfa.status_code == 401
    good_mfa = api.post("/api/v1/auth/login/mfa", json={"challenge_id": challenge.json()["challenge_id"], "code": totp_code(secret)})
    assert good_mfa.status_code == 200, good_mfa.text
    mfa_headers = {"Authorization": f"Bearer {good_mfa.json()['access_token']}"}

    second_challenge = api.post("/api/v1/auth/login", json={"identifier": "admin@fnlifting.com", "password": "Admin@12345", "portal": "staff"})
    recovery = api.post("/api/v1/auth/login/mfa", json={"challenge_id": second_challenge.json()["challenge_id"], "code": recovery_code})
    assert recovery.status_code == 200, recovery.text

    sessions = api.get("/api/v1/enterprise/sessions", headers=mfa_headers)
    assert sessions.status_code == 200
    assert sessions.json()
    revoked = api.delete(f"/api/v1/enterprise/sessions/{sessions.json()[0]['id']}", headers=mfa_headers)
    assert revoked.status_code == 200

    disabled = api.post("/api/v1/enterprise/security/mfa/disable", headers=mfa_headers)
    assert disabled.status_code == 200
    api.close()
