from app.core.security import hash_password
from app.database import crud
from app.database.models import Role

VALID_PASSWORD = "correct-horse-battery"


def _register(client, email="user@example.com", password=VALID_PASSWORD, full_name="Jane User"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def test_register_creates_user_and_sets_cookies(client):
    response = _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "GUEST"
    assert body["is_active"] is True
    assert "hashed_password" not in body
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


def test_register_as_host_sets_host_role(client):
    response = client.post(
        "/auth/register",
        json={"email": "host@example.com", "password": VALID_PASSWORD, "role": "HOST"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "HOST"


def test_register_rejects_self_registration_as_staff_role(client):
    response = client.post(
        "/auth/register",
        json={"email": "sneaky@example.com", "password": VALID_PASSWORD, "role": "SUPPORT_MANAGER"},
    )

    assert response.status_code == 422

    # Confirm no account was created despite the rejected request.
    login_attempt = client.post("/auth/login", json={"email": "sneaky@example.com", "password": VALID_PASSWORD})
    assert login_attempt.status_code == 401


def test_register_rejects_every_non_self_registerable_role(client):
    for role, email in [
        ("SUPPORT_MANAGER", "a@example.com"),
        ("OPS_MANAGER", "b@example.com"),
        ("PRODUCT_MANAGER", "c@example.com"),
        ("EXEC", "d@example.com"),
    ]:
        response = client.post(
            "/auth/register", json={"email": email, "password": VALID_PASSWORD, "role": role}
        )
        assert response.status_code == 422, f"role {role} should have been rejected"


def test_register_duplicate_email_conflicts(client):
    _register(client)
    response = _register(client)

    assert response.status_code == 409


def test_login_success_returns_role_and_sets_cookies(client):
    _register(client)

    response = client.post("/auth/login", json={"email": "user@example.com", "password": VALID_PASSWORD})

    assert response.status_code == 200
    assert response.json()["role"] == "GUEST"
    assert "access_token" in response.cookies


def test_login_wrong_password_is_unauthorized(client):
    _register(client)

    response = client.post("/auth/login", json={"email": "user@example.com", "password": "wrong-password"})

    assert response.status_code == 401


def test_login_nonexistent_email_is_unauthorized(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": VALID_PASSWORD})

    assert response.status_code == 401


def test_login_inactive_account_is_forbidden(client, db_session):
    user = crud.create_user(db_session, email="inactive@example.com", hashed_password=hash_password(VALID_PASSWORD))
    user.is_active = False
    db_session.commit()

    response = client.post("/auth/login", json={"email": "inactive@example.com", "password": VALID_PASSWORD})

    assert response.status_code == 403


def test_staff_user_logs_in_with_staff_role(client, db_session):
    crud.create_user(
        db_session,
        email="manager@example.com",
        hashed_password=hash_password(VALID_PASSWORD),
        role=Role.SUPPORT_MANAGER,
    )

    response = client.post("/auth/login", json={"email": "manager@example.com", "password": VALID_PASSWORD})

    assert response.status_code == 200
    assert response.json()["role"] == "SUPPORT_MANAGER"


def test_me_requires_authentication(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_returns_current_user_after_login(client):
    _register(client)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_update_profile_changes_full_name(client):
    _register(client)

    response = client.patch("/auth/me", json={"full_name": "Jane Q. User"})

    assert response.status_code == 200
    assert response.json()["full_name"] == "Jane Q. User"
    assert client.get("/auth/me").json()["full_name"] == "Jane Q. User"


def test_update_profile_requires_authentication(client):
    response = client.patch("/auth/me", json={"full_name": "Someone"})

    assert response.status_code == 401


def test_logout_clears_session(client):
    _register(client)
    assert client.get("/auth/me").status_code == 200

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 204

    assert client.get("/auth/me").status_code == 401


def test_change_password_requires_correct_current_password(client):
    _register(client)

    response = client.post(
        "/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "new-strong-password"},
    )

    assert response.status_code == 401


def test_change_password_success_allows_login_with_new_password(client):
    _register(client)

    response = client.post(
        "/auth/change-password",
        json={"current_password": VALID_PASSWORD, "new_password": "new-strong-password"},
    )
    assert response.status_code == 204

    client.post("/auth/logout")
    login_response = client.post(
        "/auth/login", json={"email": "user@example.com", "password": "new-strong-password"}
    )
    assert login_response.status_code == 200


def test_forgot_password_never_reveals_account_existence(client):
    _register(client)

    existing = client.post("/auth/forgot-password", json={"email": "user@example.com"})
    missing = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})

    assert existing.status_code == 200
    assert missing.status_code == 200
    assert existing.json()["detail"] == missing.json()["detail"]


def test_forgot_password_returns_stub_token_in_debug_mode(client):
    _register(client)

    response = client.post("/auth/forgot-password", json={"email": "user@example.com"})

    assert response.status_code == 200
    assert response.json()["reset_token"] is not None


def test_reset_password_with_valid_token_changes_password(client):
    _register(client)
    token = client.post("/auth/forgot-password", json={"email": "user@example.com"}).json()["reset_token"]

    reset_response = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "brand-new-password"}
    )
    assert reset_response.status_code == 204

    client.post("/auth/logout")
    login_response = client.post(
        "/auth/login", json={"email": "user@example.com", "password": "brand-new-password"}
    )
    assert login_response.status_code == 200


def test_reset_password_token_is_single_use(client):
    _register(client)
    token = client.post("/auth/forgot-password", json={"email": "user@example.com"}).json()["reset_token"]

    client.post("/auth/reset-password", json={"token": token, "new_password": "first-new-password"})
    second_attempt = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "second-new-password"}
    )

    assert second_attempt.status_code == 400


def test_reset_password_rejects_invalid_token(client):
    response = client.post(
        "/auth/reset-password", json={"token": "not-a-real-token", "new_password": "whatever-password"}
    )

    assert response.status_code == 400


def test_login_is_rate_limited_after_repeated_failures(client):
    for _ in range(5):
        client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

    assert response.status_code == 429
