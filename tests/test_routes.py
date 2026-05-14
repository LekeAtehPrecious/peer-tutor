import pytest
from app import create_app, db
from app.models import User, TutoringRequest
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = \
        "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-key"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def student(app):
    """Create a test student user."""
    with app.app_context():
        user = User(
            full_name="Test Student",
            email="student@test.com",
            password=generate_password_hash("password123"),
            role="student"
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def tutor(app):
    """Create a test tutor user."""
    with app.app_context():
        user = User(
            full_name="Test Tutor",
            email="tutor@test.com",
            password=generate_password_hash("password123"),
            role="tutor"
        )
        db.session.add(user)
        db.session.commit()
        return user


# ── TESTS ──────────────────────────────────────────


def test_home_page(client):
    """Test home page loads successfully."""
    response = client.get("/")
    assert response.status_code == 200


def test_register_page_loads(client):
    """Test register page loads successfully."""
    response = client.get("/register")
    assert response.status_code == 200


def test_login_page_loads(client):
    """Test login page loads successfully."""
    response = client.get("/login")
    assert response.status_code == 200


def test_register_new_user(client, app):
    """Test a new user can register successfully."""
    response = client.post("/register", data={
        "full_name": "Sharon Test",
        "email": "sharon@test.com",
        "password": "password123",
        "confirm_password": "password123",
        "role": "student"
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(
            email="sharon@test.com").first()
        assert user is not None
        assert user.full_name == "Sharon Test"
        assert user.role == "student"


def test_register_duplicate_email(client, app, student):
    """Test duplicate email registration is rejected."""
    response = client.post("/register", data={
        "full_name": "Another Student",
        "email": "student@test.com",
        "password": "password123",
        "confirm_password": "password123",
        "role": "student"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"already registered" in response.data


def test_login_valid_user(client, app, student):
    """Test a valid user can log in."""
    response = client.post("/login", data={
        "email": "student@test.com",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_login_invalid_password(client, app, student):
    """Test login fails with wrong password."""
    response = client.post("/login", data={
        "email": "student@test.com",
        "password": "wrongpassword"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_login_invalid_email(client):
    """Test login fails with unregistered email."""
    response = client.post("/login", data={
        "email": "nobody@test.com",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_dashboard_requires_login(client):
    """Test dashboard redirects if not logged in."""
    response = client.get("/dashboard",
                          follow_redirects=True)
    assert response.status_code == 200
    assert b"login" in response.data.lower()


def test_post_request_as_student(client, app, student):
    """Test student can post a tutoring request."""
    # Login as student first
    client.post("/login", data={
        "email": "student@test.com",
        "password": "password123"
    })

    response = client.post("/request/new", data={
        "subject": "Mathematics",
        "topic": "Calculus",
        "description": "Need help with derivatives"
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        req = TutoringRequest.query.filter_by(
            subject="Mathematics").first()
        assert req is not None
        assert req.topic == "Calculus"
        assert req.status == "open"


def test_tutor_cannot_post_request(client, app, tutor):
    """Test tutor cannot post a tutoring request."""
    client.post("/login", data={
        "email": "tutor@test.com",
        "password": "password123"
    })

    response = client.post("/request/new", data={
        "subject": "Physics",
        "topic": "Mechanics",
        "description": "Need help"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Only students" in response.data