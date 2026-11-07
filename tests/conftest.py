import pytest

from app import create_app, db
from app.constants import ROLE_ADMIN, ROLE_GESTIONNAIRE, ROLE_MAGASINIER
from app.models.user import User

PASSWORD = "MotDePasse123"


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "cle-de-test-suffisamment-longue-pour-hs256",
        "SECRET_KEY": "cle-de-test",
        "BCRYPT_ROUNDS": 4,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(email, role, is_active=True, password=PASSWORD):
    user = User(
        email=email,
        full_name=f"Test {role}",
        role=role,
        is_active=is_active
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin(app):
    return make_user("admin@test.sn", ROLE_ADMIN)


@pytest.fixture
def gestionnaire(app):
    return make_user("gestionnaire@test.sn", ROLE_GESTIONNAIRE)


@pytest.fixture
def magasinier(app):
    return make_user("magasinier@test.sn", ROLE_MAGASINIER)


def login(client, email, password=PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )


def auth_header(client, user):
    response = login(client, user.email)
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, admin):
    return auth_header(client, admin)


@pytest.fixture
def gestionnaire_headers(client, gestionnaire):
    return auth_header(client, gestionnaire)


@pytest.fixture
def magasinier_headers(client, magasinier):
    return auth_header(client, magasinier)


@pytest.fixture
def product_payload():
    return {
        "sku": "SKU-001",
        "name": "Clou 50mm",
        "description": "Boîte de 100",
        "category_id": 1,
        "unit_price": "12.50",
        "minimum_stock": 5
    }