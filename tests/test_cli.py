from app.models.user import User


def test_create_admin_command(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=[
        "create-admin",
        "--email", "Chef@Test.SN",
        "--full-name", "Chef",
        "--password", "MotDePasse123",
    ], input="MotDePasse123\n")

    assert result.exit_code == 0
    user = User.query.filter_by(email="chef@test.sn").first()
    assert user is not None
    assert user.role == "admin"
    assert user.check_password("MotDePasse123")


def test_create_admin_duplicate(app, admin):
    runner = app.test_cli_runner()

    result = runner.invoke(args=[
        "create-admin",
        "--email", admin.email,
        "--full-name", "Doublon",
        "--password", "MotDePasse123",
    ])

    assert result.exit_code != 0
    assert "existe déjà" in result.output


def test_create_admin_weak_password(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=[
        "create-admin",
        "--email", "x@test.sn",
        "--full-name", "X",
        "--password", "court",
    ])

    assert result.exit_code != 0
